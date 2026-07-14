"""User Service — FastAPI app with register / login / profile."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select

from common.config import Settings, get_settings
from common.db import init_db, session_scope
from common.errors import NotFoundError, install_exception_handlers
from common.logging import configure_logging
from common.service import bootstrap
from common.security import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from common.deps import get_token, require_user_id

from .models import User
from .schemas import LoginIn, ProfileUpdate, RegisterIn, TokenOut, UserOut

os.environ.setdefault("SERVICE_NAME", "user-service")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="User Service", version="1.0.0")
install_exception_handlers(app)

# ensure tables exist (dev/native); in Docker an init step or migration does this
init_db(settings)
bootstrap(app, settings, settings.service_urls())


@app.get("/health")
def health() -> dict:
    return {"service": settings.service_name, "status": "ok"}


@app.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        exists = s.execute(
            select(User).where((User.username == body.username) | (User.email == body.email))
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="username or email already registered")
        user = User(
            username=body.username,
            email=body.email,
            password_hash=hash_password(body.password),
            full_name=body.full_name or "",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        s.add(user)
        s.flush()
        token = create_access_token(user.id, settings)
        return TokenOut(access_token=token, user_id=user.id)


@app.post("/login", response_model=TokenOut)
def login(body: LoginIn, settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        user = s.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="invalid credentials")
        token = create_access_token(user.id, settings)
        return TokenOut(access_token=token, user_id=user.id)


@app.get("/me", response_model=UserOut)
def me(user_id: int = Depends(require_user_id)):
    with session_scope(settings) as s:
        user = s.get(User, user_id)
        if not user:
            raise NotFoundError("user not found")
        return UserOut.from_orm(user)


@app.patch("/me", response_model=UserOut)
def update_profile(
    body: ProfileUpdate,
    user_id: int = Depends(require_user_id),
    settings: Settings = Depends(get_settings),
):
    with session_scope(settings) as s:
        user = s.get(User, user_id)
        if not user:
            raise NotFoundError("user not found")
        if body.email is not None:
            user.email = body.email
        if body.full_name is not None:
            user.full_name = body.full_name
        return UserOut.from_orm(user)
