"""Payment Service — FastAPI app.

Mock mode approves any payment (status=succeeded) so the whole platform works
without external accounts. Real Stripe mode is wired via stripe.PaymentIntent.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select

from common.config import Settings, get_settings
from common.db import init_db, session_scope
from common.errors import NotFoundError, install_exception_handlers
from common.logging import configure_logging
from common.service import bootstrap
from common.events import publish

from .models import Payment
from .schemas import PayIn, PaymentOut

os.environ.setdefault("SERVICE_NAME", "payment-service")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)
# let the event bus deliver events to the Notification Service over HTTP
os.environ.setdefault("NOTIFICATION_SERVICE_URL", settings.notification_service_url)

app = FastAPI(title="Payment Service", version="1.0.0")
install_exception_handlers(app)
init_db(settings)
bootstrap(app, settings, settings.service_urls())


def _charge_stripe(amount: float, currency: str) -> tuple[str, str]:
    """Call Stripe if configured; otherwise mock-approve. Returns (status, txn_id)."""
    if settings.stripe_api_key:
        try:
            import stripe  # optional dependency
            stripe.api_key = settings.stripe_api_key
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100), currency=currency.lower(),
                automatic_payment_methods={"enabled": True},
            )
            return "succeeded", intent.id
        except Exception as e:  # noqa: BLE001
            log.error("stripe charge failed: %s", e)
            return "failed", ""
    # mock: deterministic approval
    return "succeeded", f"mock_{uuid.uuid4().hex[:12]}"


@app.get("/health")
def health() -> dict:
    return {"service": settings.service_name,
            "status": "ok", "mode": "stripe" if settings.stripe_api_key else "mock"}


@app.post("/pay", response_model=PaymentOut, status_code=201)
def pay(body: PayIn, settings: Settings = Depends(get_settings)):
    status, txn = _charge_stripe(body.amount, body.currency)
    with session_scope(settings) as s:
        p = Payment(
            order_id=body.order_id, user_id=body.user_id, amount=body.amount,
            currency=body.currency, status=status,
            transaction_id=txn, created_at=datetime.now(timezone.utc).isoformat(),
        )
        s.add(p)
        s.flush()
        pid = p.id
        out = PaymentOut.from_orm(p)
    publish("payment.completed", {"order_id": body.order_id, "user_id": body.user_id,
                                  "status": status, "transaction_id": txn,
                                  "amount": body.amount, "email": body.email})
    return out


@app.get("/payments/{order_id}", response_model=PaymentOut)
def get_payment(order_id: int, settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        p = s.execute(select(Payment).where(Payment.order_id == order_id)
                      .order_by(Payment.id.desc())).scalar_one_or_none()
        if not p:
            raise NotFoundError(f"no payment for order {order_id}")
        return PaymentOut.from_orm(p)
