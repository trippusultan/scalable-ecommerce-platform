"""Order Service schemas."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    total: float
    items: list[dict]
    created_at: str

    @classmethod
    def from_orm(cls, o: Any) -> "OrderOut":
        import json
        items = json.loads(o.items) if o.items else []
        return cls(id=o.id, user_id=o.user_id, status=o.status, total=o.total,
                   items=items, created_at=o.created_at)


class CheckoutOut(BaseModel):
    order_id: int
    status: str
    total: float
    payment_status: str
