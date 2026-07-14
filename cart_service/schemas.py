"""Cart Service schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AddItem(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class UpdateQty(BaseModel):
    quantity: int = Field(ge=1)


class CartItemOut(BaseModel):
    product_id: int
    quantity: int
