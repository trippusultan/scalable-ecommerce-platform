"""Product Catalog Service — models."""
from __future__ import annotations

from sqlalchemy import String, Integer, Float, Column, Text

from common.db import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, index=True, nullable=False)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(160), nullable=False, index=True)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    category_id = Column(Integer, index=True, nullable=True)
    stock = Column(Integer, nullable=False, default=0)
