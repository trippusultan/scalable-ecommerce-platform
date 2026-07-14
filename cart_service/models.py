"""Cart Service — models + schemas + app.

Cart resolves product names/prices lazily from the Product Catalog Service at
checkout time (the Order Service does the authoritative price+stock check).
"""
from __future__ import annotations

from sqlalchemy import String, Integer, Column, ForeignKey

from common.db import Base


class CartItem(Base):
    __tablename__ = "cart_items"
    # one cart per user; cart_id == user_id for simplicity
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    product_id = Column(Integer, index=True, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
