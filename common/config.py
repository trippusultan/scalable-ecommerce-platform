"""Per-service configuration via environment variables.

Every microservice shares this module. Override via env vars (12-factor).
A service sets its own SERVICE_NAME and DB; everything else is shared.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Settings:
    service_name: str = "service"
    host: str = "0.0.0.0"
    port: int = 8000
    # SQLite by default so the platform runs with zero infra. In Docker, set
    # DATABASE_URL to a per-service Postgres DSN.
    database_url: str = "sqlite:///./data/{service}.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    # Knobs
    log_level: str = "INFO"
    # External (optional) integrations — absent => safe mock mode
    stripe_api_key: str = ""
    sendgrid_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    # Event bus: "memory" (single-process/dev) or "rabbitmq"
    event_bus: str = "memory"
    rabbitmq_url: str = "amqp://guest:***@localhost:5672/"
    # Comma-separated list of service base URLs for service-to-service calls,
    # e.g. USER_SERVICE_URL=http://user-service:8001
    # NOTE: use 127.0.0.1 (not "localhost") so httpx doesn't resolve to IPv6 ::1
    # while uvicorn binds IPv4 — that mismatch makes service-to-service calls hang.
    user_service_url: str = "http://127.0.0.1:8001"
    product_service_url: str = "http://127.0.0.1:8002"
    cart_service_url: str = "http://127.0.0.1:8003"
    payment_service_url: str = "http://127.0.0.1:8004"
    order_service_url: str = "http://127.0.0.1:8005"
    notification_service_url: str = "http://127.0.0.1:8006"

    def resolve_db_url(self) -> str:
        return self.database_url.format(service=self.service_name)

    def service_urls(self) -> dict[str, str]:
        """Static fallback map of every service name -> base URL."""
        return {
            "user-service": self.user_service_url,
            "product-service": self.product_service_url,
            "cart-service": self.cart_service_url,
            "payment-service": self.payment_service_url,
            "order-service": self.order_service_url,
            "notification-service": self.notification_service_url,
            "gateway": "http://127.0.0.1:8000",
        }

    @classmethod
    def load(cls, service_name: str, **overrides: Any) -> "Settings":
        s = cls(service_name=service_name)
        mapping = {
            "HOST": "host", "PORT": "port", "DATABASE_URL": "database_url",
            "JWT_SECRET": "jwt_secret", "JWT_ALGORITHM": "jwt_algorithm",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "access_token_expire_minutes",
            "LOG_LEVEL": "log_level", "STRIPE_API_KEY": "stripe_api_key",
            "SENDGRID_API_KEY": "sendgrid_api_key",
            "TWILIO_ACCOUNT_SID": "twilio_account_sid",
            "TWILIO_AUTH_TOKEN": "twilio_auth_token",
            "TWILIO_FROM_NUMBER": "twilio_from_number",
            "EVENT_BUS": "event_bus", "RABBITMQ_URL": "rabbitmq_url",
            "USER_SERVICE_URL": "user_service_url",
            "PRODUCT_SERVICE_URL": "product_service_url",
            "CART_SERVICE_URL": "cart_service_url",
            "PAYMENT_SERVICE_URL": "payment_service_url",
            "ORDER_SERVICE_URL": "order_service_url",
            "NOTIFICATION_SERVICE_URL": "notification_service_url",
        }
        for env_key, attr in mapping.items():
            if env_key in os.environ:
                val = os.environ[env_key]
                if attr in ("port", "access_token_expire_minutes"):
                    val = int(val)
                setattr(s, attr, val)
        for k, v in overrides.items():
            setattr(s, k, v)
        return s


# A tiny module-level cache so tests can override via monkeypatch on get_settings.
_SETTINGS: dict[str, Settings] = {}


def get_settings() -> Settings:
    # Returns the settings for whatever service imported common; callers should
    # set the right service name. We read from env SERVICE_NAME if present.
    name = os.environ.get("SERVICE_NAME", "service")
    if name not in _SETTINGS:
        _SETTINGS[name] = Settings.load(name)
    return _SETTINGS[name]


def set_settings(s: Settings) -> None:
    _SETTINGS[s.service_name] = s
