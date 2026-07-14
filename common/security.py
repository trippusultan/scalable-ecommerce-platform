"""Auth: password hashing (bcrypt) + JWT access tokens."""
from __future__ import annotations

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import Settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | int, settings: Settings, extra: dict[str, Any] | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Returns the payload, or raises jwt.PyJWTError on invalid/expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_current_user_id(token: str, settings: Settings) -> int:
    """Decode a bearer token and return the user id (int). Raises on failure."""
    payload = decode_access_token(token, settings)
    return int(payload["sub"])
