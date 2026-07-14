"""Order Service — FastAPI app (orchestrator).

Checkout flow:
  1. fetch cart from Cart Service
  2. for each item, GET product from Product Service (price + stock)
  3. reserve stock (PATCH product stock delta=-qty); abort if any unavailable
  4. POST payment to Payment Service
  5. create order (status paid/confirmed), clear cart
  6. emit order.placed -> Notification Service

On any failure after stock reservation, release stock and cancel the order.
"""
from __future__ import annotations

import os
import json
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select

from common.client import ServiceClient, ServiceError
from common.config import Settings, get_settings
from common.db import init_db, session_scope
from common.deps import get_token, require_user_id
from common.discovery import DiscoveryClient
from common.errors import NotFoundError, install_exception_handlers
from common.events import publish
from common.logging import configure_logging
from common.service import bootstrap

from .models import Order, OrderItem
from .schemas import CheckoutOut, OrderOut

os.environ.setdefault("SERVICE_NAME", "order-service")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)
# let the event bus deliver events to the Notification Service over HTTP
os.environ.setdefault("NOTIFICATION_SERVICE_URL", settings.notification_service_url)
# Resolve downstream services via the discovery registry when available
# (falls back to the static *_SERVICE_URL defaults otherwise).
_discovery = DiscoveryClient(os.environ.get("DISCOVERY_URL", ""), settings.service_urls())

app = FastAPI(title="Order Service", version="1.0.0")
install_exception_handlers(app)
init_db(settings)
bootstrap(app, settings, settings.service_urls())


@app.get("/health")
def health() -> dict:
    return {"service": settings.service_name, "status": "ok"}


@app.post("/checkout", response_model=CheckoutOut, status_code=201)
async def checkout(user_id: int = Depends(require_user_id),
                   token: str = Depends(get_token),
                   settings: Settings = Depends(get_settings)):
    cart = ServiceClient(settings.cart_service_url, discovery=_discovery, service_name="cart-service")
    product = ServiceClient(settings.product_service_url, discovery=_discovery, service_name="product-service")
    payment = ServiceClient(settings.payment_service_url, discovery=_discovery, service_name="payment-service")
    user = ServiceClient(settings.user_service_url, discovery=_discovery, service_name="user-service")
    reserved: list[int] = []
    try:
        # 1) cart
        items = await cart.get("/cart", token=token) or []
        if not items:
            raise HTTPException(status_code=400, detail="cart is empty")
        # resolve the user's email for downstream notifications
        try:
            profile = await user.get("/me", token=token) or {}
            user_email = profile.get("email", "")
        except ServiceError:
            user_email = ""
        # 2) resolve products
        lines = []
        total = 0.0
        for it in items:
            pid = it["product_id"]
            qty = it["quantity"]
            p = await product.get(f"/products/{pid}")
            if p["stock"] < qty:
                raise HTTPException(status_code=409,
                                    detail=f"product {pid} only has {p['stock']} in stock")
            lines.append({"product_id": pid, "quantity": qty, "price": p["price"]})
            total += p["price"] * qty
            # 3) reserve stock
            res = await product.patch(f"/products/{pid}/stock",
                                       json={"product_id": pid, "delta": -qty})
            if not res.get("ok"):
                raise HTTPException(status_code=409, detail=f"product {pid} out of stock")
            reserved.append(pid)
        # 4) pay
        pay = await payment.post("/pay", json={"order_id": 0, "user_id": user_id,
                                               "amount": round(total, 2),
                                               "currency": "USD", "email": user_email},
                                 token=token)
        pay_status = pay["status"]
        # 5) persist order
        with session_scope(settings) as s:
            o = Order(user_id=user_id, status="confirmed" if pay_status == "succeeded" else "cancelled",
                      total=round(total, 2), items=json.dumps(lines),
                      created_at=datetime.now(timezone.utc).isoformat())
            s.add(o)
            s.flush()
            for ln in lines:
                s.add(OrderItem(order_id=o.id, product_id=ln["product_id"],
                                quantity=ln["quantity"], price=ln["price"]))
            order_id = o.id
            order_status = o.status
        # 6) clear cart + notify
        await cart.delete("/cart", token=token)
        publish("order.placed", {"order_id": order_id, "user_id": user_id,
                                 "email": user_email, "total": round(total, 2),
                                 "status": order_status, "items": lines})
        return CheckoutOut(order_id=order_id, status=order_status,
                           total=round(total, 2), payment_status=pay_status)
    except ServiceError as e:
        # release any reserved stock so inventory isn't stranded
        for pid in reserved:
            try:
                await product.patch(f"/products/{pid}/stock",
                                     json={"product_id": pid, "delta": 1})
            except Exception:  # noqa: BLE001
                log.warning("failed to release stock for product %s after error", pid)
        raise HTTPException(status_code=502, detail=f"checkout failed: {e}")
    finally:
        await cart.close()
        await product.close()
        await payment.close()
        await user.close()


@app.get("/orders", response_model=list[OrderOut])
def list_orders(user_id: int = Depends(require_user_id), settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        rows = s.execute(select(Order).where(Order.user_id == user_id)
                         .order_by(Order.id.desc())).scalars().all()
        return [OrderOut.from_orm(o) for o in rows]


@app.get("/orders/{oid}", response_model=OrderOut)
def get_order(oid: int, user_id: int = Depends(require_user_id),
              settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        o = s.get(Order, oid)
        if not o or o.user_id != user_id:
            raise NotFoundError("order not found")
        return OrderOut.from_orm(o)
