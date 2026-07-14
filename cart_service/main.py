"""Cart Service — FastAPI app."""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from common.config import Settings, get_settings
from common.db import init_db, session_scope
from common.deps import require_user_id
from common.errors import install_exception_handlers
from common.logging import configure_logging
from common.service import bootstrap

from .models import CartItem
from .schemas import AddItem, CartItemOut, UpdateQty

os.environ.setdefault("SERVICE_NAME", "cart-service")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="Shopping Cart Service", version="1.0.0")
install_exception_handlers(app)
init_db(settings)
bootstrap(app, settings, settings.service_urls())


@app.get("/health")
def health() -> dict:
    return {"service": settings.service_name, "status": "ok"}


@app.get("/cart", response_model=list[CartItemOut])
def view_cart(user_id: int = Depends(require_user_id), settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        rows = s.execute(select(CartItem).where(CartItem.user_id == user_id)).scalars().all()
        return [CartItemOut(product_id=r.product_id, quantity=r.quantity) for r in rows]


@app.post("/cart/items", response_model=list[CartItemOut], status_code=201)
def add_item(body: AddItem, user_id: int = Depends(require_user_id),
             settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        item = s.execute(
            select(CartItem).where(CartItem.user_id == user_id,
                                   CartItem.product_id == body.product_id)
        ).scalar_one_or_none()
        if item:
            item.quantity += body.quantity
        else:
            item = CartItem(user_id=user_id, product_id=body.product_id, quantity=body.quantity)
            s.add(item)
        s.flush()
        rows = s.execute(select(CartItem).where(CartItem.user_id == user_id)).scalars().all()
        return [CartItemOut(product_id=r.product_id, quantity=r.quantity) for r in rows]


@app.patch("/cart/items/{product_id}", response_model=list[CartItemOut])
def update_qty(product_id: int, body: UpdateQty, user_id: int = Depends(require_user_id),
               settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        item = s.execute(
            select(CartItem).where(CartItem.user_id == user_id,
                                   CartItem.product_id == product_id)
        ).scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="item not in cart")
        item.quantity = body.quantity
        rows = s.execute(select(CartItem).where(CartItem.user_id == user_id)).scalars().all()
        return [CartItemOut(product_id=r.product_id, quantity=r.quantity) for r in rows]


@app.delete("/cart/items/{product_id}", response_model=list[CartItemOut])
def remove_item(product_id: int, user_id: int = Depends(require_user_id),
                settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        s.execute(
            sa_delete(CartItem).where(CartItem.user_id == user_id,
                                      CartItem.product_id == product_id)
        )
        rows = s.execute(select(CartItem).where(CartItem.user_id == user_id)).scalars().all()
        return [CartItemOut(product_id=r.product_id, quantity=r.quantity) for r in rows]


@app.delete("/cart", status_code=204)
def clear_cart(user_id: int = Depends(require_user_id), settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        s.execute(sa_delete(CartItem).where(CartItem.user_id == user_id))
