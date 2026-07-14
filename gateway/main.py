"""API Gateway — single entry point.

Routes client requests to the correct microservice and forwards the bearer JWT
so downstream services can authorize. Health aggregation at /health.

Routes (strip the /api/<service> prefix):
  /api/users/*      -> user-service
  /api/products/*   -> product-service
  /api/cart/*       -> cart-service
  /api/orders/*     -> order-service
  /api/payments/*   -> payment-service
  /api/notify/*     -> notification-service

The gateway resolves each target via the service-discovery registry when
DISCOVERY_URL is set, falling back to static *_SERVICE_URL env values. It only
forwards; it does NOT re-implement business logic. Auth is enforced by each
service via the forwarded token.
"""
from __future__ import annotations

import asyncio
import os
import threading
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from common.config import Settings, get_settings
from common.discovery import DiscoveryClient
from common.errors import install_exception_handlers
from common.logging import configure_logging
from common.service import bootstrap

os.environ.setdefault("SERVICE_NAME", "gateway")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="API Gateway", version="1.0.0")
install_exception_handlers(app)

# logical prefix -> registry service name
SERVICE_NAMES = {
    "users": "user-service",
    "products": "product-service",
    "cart": "cart-service",
    "orders": "order-service",
    "payments": "payment-service",
    "notify": "notification-service",
}

_registry = DiscoveryClient(
    os.environ.get("DISCOVERY_URL", ""), settings.service_urls()
)
# NOTE: the httpx client is created per-request (see _client()) rather than at
# module import time. A module-level AsyncClient binds to whichever event loop
# existed at import, which is NOT the one uvicorn runs requests on — every call
# would then fail silently. Per-request clients are correct and cheap enough
# here.
bootstrap(app, settings, settings.service_urls())


def _resolve(name: str) -> str:
    """Registry-first resolution; falls back to static env URL."""
    return _registry.resolve(name)


# --- Health aggregation (lazy / non-blocking) ---------------------------------
# /health returns a snapshot from an in-memory cache that a background thread
# refreshes on an interval. This keeps the endpoint instant (<1ms) instead of
# fanning out to every downstream on each call (which could take seconds and
# time out health probes). The snapshot is always at most one interval stale.
_HEALTH_CACHE: dict[str, str] = {prefix: "unknown" for prefix in SERVICE_NAMES}
_HEALTH_LOCK = threading.Lock()


def _refresh_health_snapshot() -> None:
    """Synchronously probe each downstream /health and update the cache."""
    import requests

    snapshot: dict[str, str] = {}
    for prefix, svc in SERVICE_NAMES.items():
        base = _resolve(svc)
        try:
            r = requests.get(f"{base}/health", timeout=2)
            snapshot[prefix] = r.json().get("status", "up") if r.status_code == 200 else "down"
        except Exception:  # noqa: BLE001
            snapshot[prefix] = "down"
    with _HEALTH_LOCK:
        _HEALTH_CACHE.clear()
        _HEALTH_CACHE.update(snapshot)


def _health_poller(interval: int = 5) -> None:
    while True:
        try:
            _refresh_health_snapshot()
        except Exception:  # noqa: BLE001
            pass
        threading.Event().wait(interval)


_thread = threading.Thread(target=_health_poller, daemon=True)
_thread.start()


async def _client() -> httpx.AsyncClient:
    # 5s is plenty for intra-cluster calls; keeps proxy failures snappy
    # instead of hanging for 30s on a dead upstream.
    return httpx.AsyncClient(timeout=5.0)


@app.get("/")
async def index() -> dict:
    return {
        "service": "API Gateway",
        "status": "ok",
        "discovery": "registry" if _registry.using_registry else "static",
        "docs": {prefix: f"{_resolve(svc)}/docs" for prefix, svc in SERVICE_NAMES.items()},
        "routes": {
            "GET /health": "aggregated health of all services (cached, ~5s fresh)",
            "POST /api/users/register": "create a user (no auth)",
            "POST /api/users/login": "get a JWT (no auth)",
            "GET /api/products/products": "list products (no auth)",
            "GET /api/cart/cart": "your cart (Bearer token required)",
            "POST /api/orders/checkout": "place an order (Bearer token required)",
        },
        "try": "POST /api/users/register then use the returned token as 'Authorization: Bearer ***'",
    }


@app.get("/health")
async def health(deep: bool = False) -> dict:
    # Default: return the last background-refreshed snapshot instantly (no
    # synchronous fan-out, so the endpoint stays fast/flaky-free).
    if not deep:
        with _HEALTH_LOCK:
            snapshot = dict(_HEALTH_CACHE)
        return {"gateway": "ok", "services": snapshot, "mode": "cached"}

    # deep=1: live fan-out to every downstream right now (slower, but real-time).
    async def _check(prefix: str, svc: str):
        base = _resolve(svc)
        try:
            async with await _client() as c:
                r = await c.get(f"{base}/health")
            return prefix, (r.json().get("status", "up") if r.status_code == 200 else "down")
        except Exception:  # noqa: BLE001
            return prefix, "down"

    import asyncio

    results = await asyncio.gather(*(_check(p, s) for p, s in SERVICE_NAMES.items()))
    return {"gateway": "ok", "services": dict(results), "mode": "deep"}


@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    if service not in SERVICE_NAMES:
        return JSONResponse(status_code=404, content={"detail": f"unknown service '{service}'"})
    target_base = _resolve(SERVICE_NAMES[service])
    if not target_base:
        return JSONResponse(status_code=502, content={"detail": f"no endpoint for '{service}'"})
    target = f"{target_base}/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    body = await request.body()
    try:
        async with await _client() as c:
            upstream = await c.request(
                request.method, target, headers=headers, params=request.query_params, content=body
            )
    except httpx.HTTPError as e:
        return JSONResponse(status_code=502, content={"detail": f"upstream error: {e}"})
    return StreamingResponse(
        content=iter([upstream.content]),
        status_code=upstream.status_code,
        headers={"Content-Type": upstream.headers.get("content-type", "application/json")},
    )
