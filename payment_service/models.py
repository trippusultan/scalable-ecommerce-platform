"""Payment Service — models + schemas.

In 'mock' mode (no STRIPE_API_KEY) it approves payments locally and is fully
deterministic for tests. With STRIPE_API_KEY set, it calls Stripe's PaymentIntent
API (the Stripe SDK is an optional dependency). Either way the external surface
is identical: POST /pay {order_id, amount, currency} -> {status, transaction_id}.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Column

from common.db import Base


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    status = Column(String(16), default="pending")  # pending|succeeded|failed
    transaction_id = Column(String(64), default="")
    created_at = Column(String(32), default="")
