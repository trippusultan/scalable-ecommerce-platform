"""User Service — request/response schemas."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str

    @classmethod
    def from_orm(cls, u: Any) -> "UserOut":
        return cls(id=u.id, username=u.username, email=u.email,
                   full_name=u.full_name or "")


class ProfileUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
