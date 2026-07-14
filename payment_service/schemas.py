"""Payment Service schemas."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PayIn(BaseModel):
    order_id: int
    user_id: int
    amount: float = Field(gt=0)
    currency: str = "USD"
    email: str = ""  # optional; forwarded to payment.completed for notifications


class PaymentOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    amount: float
    currency: str
    status: str
    transaction_id: str

    @classmethod
    def from_orm(cls, p: Any) -> "PaymentOut":
        return cls(id=p.id, order_id=p.order_id, user_id=p.user_id, amount=p.amount,
                   currency=p.currency, status=p.status, transaction_id=p.transaction_id)
