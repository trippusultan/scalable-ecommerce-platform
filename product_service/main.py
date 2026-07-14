"""Product Catalog Service — FastAPI app."""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select

from common.config import Settings, get_settings
from common.db import init_db, session_scope
from common.errors import NotFoundError, install_exception_handlers
from common.logging import configure_logging
from common.service import bootstrap

from .models import Category, Product
from .schemas import (
    CategoryCreate,
    CategoryOut,
    InventoryOp,
    ProductCreate,
    ProductOut,
    StockResult,
)

os.environ.setdefault("SERVICE_NAME", "product-service")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="Product Catalog Service", version="1.0.0")
install_exception_handlers(app)
init_db(settings)
bootstrap(app, settings, settings.service_urls())


def _get_product(s, pid: int) -> Product:
    p = s.get(Product, pid)
    if not p:
        raise NotFoundError(f"product {pid} not found")
    return p


@app.get("/health")
def health() -> dict:
    return {"service": settings.service_name, "status": "ok"}


@app.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryCreate, settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        if s.execute(select(Category).where(Category.name == body.name)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail="category exists")
        c = Category(name=body.name)
        s.add(c)
        s.flush()
        return CategoryOut(id=c.id, name=c.name)


@app.get("/categories", response_model=list[CategoryOut])
def list_categories(settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        return [CategoryOut(id=c.id, name=c.name) for c in s.execute(select(Category)).scalars()]


@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        p = Product(name=body.name, description=body.description, price=body.price,
                    stock=body.stock, category_id=body.category_id)
        s.add(p)
        s.flush()
        return ProductOut.from_orm(p)


@app.get("/products", response_model=list[ProductOut])
def list_products(category_id: int | None = None, settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        stmt = select(Product)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        return [ProductOut.from_orm(p) for p in s.execute(stmt).scalars()]


@app.get("/products/{pid}", response_model=ProductOut)
def get_product(pid: int, settings: Settings = Depends(get_settings)):
    with session_scope(settings) as s:
        return ProductOut.from_orm(_get_product(s, pid))


@app.patch("/products/{pid}/stock", response_model=StockResult)
def adjust_stock(pid: int, op: InventoryOp, settings: Settings = Depends(get_settings)):
    """Reserve (delta<0) or restock (delta>0). Called by Order Service.

    Convention: order placement sends delta = -qty (reserve). If stock would go
    negative, returns ok=False (order service then aborts the order).
    """
    with session_scope(settings) as s:
        p = _get_product(s, pid)
        new_stock = p.stock + op.delta
        if new_stock < 0:
            return StockResult(product_id=pid, stock=p.stock, ok=False)
        p.stock = new_stock
        return StockResult(product_id=pid, stock=p.stock, ok=True)
