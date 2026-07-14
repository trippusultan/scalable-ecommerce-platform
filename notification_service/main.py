"""Notification Service — listens for domain events and sends email/SMS.

Modes:
  - email: SendGrid if SENDGRID_API_KEY set, else mock (logs the message)
  - sms:   Twilio if TWILIO_* set, else mock (logs the message)

It subscribes to the event bus for 'order.placed', 'payment.completed', etc.
With the in-memory bus (dev) the subscription is wired at app startup via a
lifespan hook. With RabbitMQ, it consumes continuously.
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from common.config import Settings, get_settings
from common.db import init_db
from common.errors import install_exception_handlers
from common.events import EventBus
from common.logging import configure_logging
from common.service import bootstrap

os.environ.setdefault("SERVICE_NAME", "notification-service")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="Notification Service", version="1.0.0")
install_exception_handlers(app)
init_db(settings)
bootstrap(app, settings, settings.service_urls())


def send_email(to: str, subject: str, body: str) -> str:
    if settings.sendgrid_api_key:
        try:
            import sendgrid  # optional
            from sendgrid.helpers.mail import Mail
            sg = sendgrid.SendGridAPIClient(settings.sendgrid_api_key)
            msg = Mail(from_email="noreply@shop.local", to_emails=to,
                       subject=subject, plain_text_content=body)
            sg.send(msg)
            return "sent"
        except Exception as e:  # noqa: BLE001
            log.error("sendgrid error: %s", e)
            return "failed"
    log.info("[email:mock] to=%s subject=%s body=%s", to, subject, body)
    return "mock"


def send_sms(to: str, body: str) -> str:
    if settings.twilio_account_sid and settings.twilio_auth_token:
        try:
            from twilio.rest import Client  # optional
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            client.messages.create(body=body, from_=settings.twilio_from_number, to=to)
            return "sent"
        except Exception as e:  # noqa: BLE001
            log.error("twilio error: %s", e)
            return "failed"
    log.info("[sms:mock] to=%s body=%s", to, body)
    return "mock"


def _recipient(p: dict) -> str:
    """Real recipient email from the event; falls back to a configured default
    (empty by default -> caller should skip if still empty, no mock address)."""
    return p.get("email") or os.environ.get("DEFAULT_NOTIFY_EMAIL", "")


def _phone() -> str:
    return os.environ.get("DEFAULT_NOTIFY_PHONE", "")


def handle_order_placed(event: dict) -> None:
    p = event.get("payload", {})
    subject = f"Order #{p.get('order_id')} confirmed"
    body = (f"Thanks! Your order #{p.get('order_id')} (total ${p.get('total')}) "
            f"is {p.get('status')}.")
    to = _recipient(p)
    if to:
        send_email(to, subject, body)
    else:
        log.warning("order.placed: no recipient email (set DEFAULT_NOTIFY_EMAIL or include email in event)")
    phone = _phone()
    if phone:
        send_sms(phone, f"Order #{p.get('order_id')} {p.get('status')}.")


def handle_payment(event: dict) -> None:
    p = event.get("payload", {})
    to = _recipient(p)
    if to:
        send_email(to, f"Payment {p.get('status')}",
                   f"Payment for order {p.get('order_id')}: {p.get('status')}.")
    else:
        log.warning("payment.completed: no recipient email")


_SUBSCRIPTIONS = {
    "order.placed": handle_order_placed,
    "payment.completed": handle_payment,
}


@app.on_event("startup")
def _wire_bus() -> None:
    bus = EventBus(backend=settings.event_bus, url=settings.rabbitmq_url)
    if settings.event_bus == "memory":
        for name, handler in _SUBSCRIPTIONS.items():
            bus.subscribe(name, handler)
        log.info("notification service subscribed to in-memory bus")


@app.get("/health")
def health() -> dict:
    return {"service": settings.service_name, "status": "ok",
            "email_mode": "sendgrid" if settings.sendgrid_api_key else "mock",
            "sms_mode": "twilio" if settings.twilio_account_sid else "mock"}


@app.post("/rpc/event")
def rpc_event(event: dict) -> JSONResponse:
    """Receive an event delivered over HTTP (native multi-process mode, no broker)."""
    name = event.get("event")
    handler = _SUBSCRIPTIONS.get(name)
    if handler:
        handler(event)
        return JSONResponse({"detail": f"handled {name}"})
    return JSONResponse({"detail": f"no handler for {name}"}, status_code=200)


@app.post("/notify/test")
def notify_test(email: str | None = None, phone: str | None = None) -> JSONResponse:
    """Manual trigger for an operator to validate delivery. Requires a real
    recipient (no mock default)."""
    to = email or os.environ.get("DEFAULT_NOTIFY_EMAIL", "")
    if not to:
        return JSONResponse({"detail": "provide ?email= or set DEFAULT_NOTIFY_EMAIL"},
                            status_code=400)
    send_email(to, "Test", "Hello from Notification Service")
    if phone:
        send_sms(phone, "Test SMS")
    return JSONResponse({"detail": f"test notification dispatched to {to}"})
