"""FastAPI dependency helpers — extract the bearer token from a request."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings
from .security import get_current_user_id


def get_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth.split(" ", 1)[1]


def require_user_id(
    token: str = Depends(get_token),
    settings: Settings = Depends(get_settings),
) -> int:
    try:
        return get_current_user_id(token, settings)
    except Exception as e:  # jwt errors
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
