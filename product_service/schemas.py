"""Product Catalog Service — schemas + inventory ops."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class CategoryOut(BaseModel):
    id: int
    name: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    category_id: int | None = None
    description: str = ""


class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category_id: int | None
    category_name: str | None = None
    stock: int

    @classmethod
    def from_orm(cls, p: Any) -> "ProductOut":
        return cls(id=p.id, name=p.name, description=p.description or "",
                   price=p.price, category_id=p.category_id,
                   category_name=(p.category.name if getattr(p, "category", None) else None),
                   stock=p.stock)


class ProductUpdate(BaseModel):
    """Partial update — all fields optional."""
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    category_id: int | None = None


class InventoryOp(BaseModel):
    """Reserve/release stock for order placement. amount>0 reserve, <0 release."""

    product_id: int
    delta: int


class StockResult(BaseModel):
    product_id: int
    stock: int
    ok: bool
