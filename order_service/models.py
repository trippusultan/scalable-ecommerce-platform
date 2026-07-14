"""Order Service — models + schemas.

An Order aggregates line items (resolved from the Product Catalog at order time)
and an overall status machine:
  pending -> (payment.ok) -> paid -> (stock reserved) -> confirmed
  any failure -> cancelled (stock released, payment refunded)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Column, Text

from common.db import Base


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    status = Column(String(16), default="pending")  # pending|paid|confirmed|cancelled
    total = Column(Float, default=0.0)
    items = Column(Text, default="")  # JSON list of {product_id, qty, price}
    created_at = Column(String(32), default="")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, index=True, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
