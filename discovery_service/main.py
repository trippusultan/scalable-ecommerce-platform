"""Service Discovery Registry (Consul-style, lightweight).

Stores service instances in SQLite (survives restarts), expires entries that
miss heartbeats, and serves lookups. Each microservice registers on startup and
sends heartbeats; the gateway (and any service) resolves peers via GET /services.

Endpoints:
  PUT    /register            {name, url, health_url?}
  PUT    /heartbeat           {name}
  GET    /services            -> {name: {url, health_url, last_seen, status}}
  GET    /services/{name}
  DELETE /services/{name}
  GET    /health
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import Column, Integer, String, delete as sa_delete, select
from sqlalchemy.orm import Session

from common.config import Settings, get_settings
from common.db import Base, get_engine, init_db
from common.errors import install_exception_handlers
from common.logging import configure_logging

os.environ.setdefault("SERVICE_NAME", "discovery-service")
settings: Settings = get_settings()
log = configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="Service Discovery", version="1.0.0")
install_exception_handlers(app)


class ServiceInstance(Base):
    __tablename__ = "service_instances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, index=True)
    url = Column(String(255))
    health_url = Column(String(255))
    last_seen = Column(String(32))
    status = Column(String(16), default="up")


init_db(settings)
_engine = get_engine(settings)
_LOCK = threading.Lock()
_TTL_SECONDS = int(os.environ.get("DISCOVERY_TTL", "30"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_fresh(last_seen: str) -> bool:
    """True if last_seen is within the TTL window."""
    try:
        ts = datetime.fromisoformat(last_seen)
    except (ValueError, TypeError):
        return False
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age <= _TTL_SECONDS


def _sweep() -> None:
    """Mark instances that missed heartbeats beyond TTL as 'down' (lazy sweep)."""
    with _LOCK, Session(_engine) as s:
        rows = s.execute(select(ServiceInstance)).scalars().all()
        for r in rows:
            fresh = _is_fresh(r.last_seen)
            desired = "up" if fresh else "down"
            if r.status != desired:
                r.status = desired
        s.commit()


@app.get("/health")
def health() -> dict:
    with Session(_engine) as s:
        n = s.execute(select(ServiceInstance)).scalars().all()
    return {"service": settings.service_name, "status": "ok", "registered": len(n)}


@app.put("/register")
def register(body: dict):
    name = body.get("name")
    url = body.get("url")
    if not name or not url:
        raise HTTPException(status_code=400, detail="name and url required")
    health_url = body.get("health_url") or f"{url}/health"
    with _LOCK, Session(_engine) as s:
        inst = s.execute(select(ServiceInstance).where(ServiceInstance.name == name)).scalar_one_or_none()
        if inst:
            inst.url = url
            inst.health_url = health_url
            inst.last_seen = _now()
            inst.status = "up"
        else:
            s.add(ServiceInstance(name=name, url=url, health_url=health_url, last_seen=_now(), status="up"))
        s.commit()
    log.info("registered %s -> %s", name, url)
    return {"detail": f"registered {name}", "url": url}


@app.put("/heartbeat")
def heartbeat(body: dict):
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    with _LOCK, Session(_engine) as s:
        inst = s.execute(select(ServiceInstance).where(ServiceInstance.name == name)).scalar_one_or_none()
        if not inst:
            raise HTTPException(status_code=404, detail="service not registered")
        inst.last_seen = _now()
        inst.status = "up"
        s.commit()
    return {"detail": "ok"}


@app.delete("/services/{name}")
def deregister(name: str):
    with _LOCK, Session(_engine) as s:
        s.execute(sa_delete(ServiceInstance).where(ServiceInstance.name == name))
        s.commit()
    return {"detail": f"deregistered {name}"}


@app.get("/services")
def list_services() -> dict:
    _sweep()
    with Session(_engine) as s:
        rows = s.execute(select(ServiceInstance)).scalars().all()
    return {
        r.name: {"url": r.url, "health_url": r.health_url,
                 "last_seen": r.last_seen, "status": r.status}
        for r in rows
    }


@app.get("/services/{name}")
def get_service(name: str):
    _sweep()
    with Session(_engine) as s:
        r = s.execute(select(ServiceInstance).where(ServiceInstance.name == name)).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="not found")
    return {"name": r.name, "url": r.url, "health_url": r.health_url,
            "last_seen": r.last_seen, "status": r.status}


# Background sweep: periodically flip stale entries to "down" so the registry
# reflects reality without waiting for a lookup.
def _sweeper() -> None:
    while True:
        _sweep()
        threading.Event().wait(max(_TTL_SECONDS, 5))


_sweep_thread = threading.Thread(target=_sweeper, daemon=True)
_sweep_thread.start()
