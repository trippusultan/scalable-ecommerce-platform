"""Shared utilities for all e-commerce microservices.

Each service imports from `common` for: settings, database session, JWT auth,
logging, inter-service HTTP client, and the event bus (used to decouple
Order -> Notification / Payment callbacks).
"""
from __future__ import annotations

from .config import Settings, get_settings
from .db import Base, get_engine, init_db, session_scope
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user_id,
)
from .logging import configure_logging
from .events import EventBus, publish
from .client import ServiceClient

__all__ = [
    "Settings", "get_settings",
    "Base", "get_engine", "init_db", "session_scope",
    "hash_password", "verify_password", "create_access_token",
    "decode_access_token", "get_current_user_id",
    "configure_logging",
    "EventBus", "publish", "ServiceClient",
]
