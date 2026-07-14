"""Shared service bootstrap: wires logging, metrics (/metrics), and service
discovery (register + heartbeat) into a FastAPI app. Every service calls this
so behavior is consistent.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Iterable

from fastapi import FastAPI, Response

from .config import Settings
from .discovery import DiscoveryClient
from .logging import configure_logging
from .metrics import MetricsMiddleware, get_metrics


def bootstrap(app: FastAPI, settings: Settings, static_urls: dict[str, str]) -> DiscoveryClient:
    """Attach metrics + discovery to an already-created app.

    - adds GET /metrics (Prometheus text)
    - registers this service with the discovery registry and starts a heartbeat
      thread (no-op if registry is unreachable — falls back to static URLs)
    - warns loudly (but does not crash) if the JWT secret is too weak for HS256
    """
    log = configure_logging(settings.service_name, settings.log_level)
    metrics = get_metrics(settings.service_name)
    app.add_middleware(MetricsMiddleware, metrics=metrics)

    @app.get("/metrics")
    def metrics_endpoint() -> Response:
        return Response(get_metrics(settings.service_name).render(),
                        media_type="text/plain; version=0.0.4")

    # security hardening: HS256 needs >= 32 bytes of key material for safety.
    # We only warn (don't fail) so dev clusters still boot, but production must
    # set a strong JWT_SECRET (and the warning goes to stderr so it's visible).
    _check_jwt_secret(settings, log)

    # discovery
    registry_url = os.environ.get("DISCOVERY_URL", "").rstrip("/")
    client = DiscoveryClient(registry_url, static_urls) if registry_url else DiscoveryClient("", static_urls)
    # Register with the URL we actually listen on (settings.port), not the static
    # default — in tests/non-default deployments the real port differs.
    self_url = f"http://127.0.0.1:{settings.port}"
    if registry_url:
        # Retry the initial registration: discovery may still be starting up
        # when this service boots, and a single failed register would leave the
        # service absent from the registry (heartbeats 404 for unregistered
        # names). Retry every second until it lands so peers can find us.
        for attempt in range(30):
            if client.register(settings.service_name, self_url, f"{self_url}/health"):
                break
            time.sleep(1)

        def _beat() -> None:
            interval = int(os.environ.get("DISCOVERY_HEARTBEAT", "5"))
            while True:
                # (re)register every beat: belt-and-suspenders in case a
                # registration was ever missed.
                client.register(settings.service_name, self_url, f"{self_url}/health")
                client.heartbeat(settings.service_name)
                threading.Event().wait(interval)

        t = threading.Thread(target=_beat, daemon=True)
        t.start()
    else:
        log.info("discovery disabled (set DISCOVERY_URL to enable); using static URLs")

    return client


def _check_jwt_secret(settings: Settings, log) -> None:
    import sys
    secret = settings.jwt_secret or ""
    # HS256 minimum recommended key length is 32 bytes (RFC 7518 §3.2).
    if len(secret.encode()) < 32:
        msg = (
            f"WEAK JWT_SECRET ({len(secret.encode())} bytes) for {settings.service_name}. "
            f"Set JWT_SECRET to a >=32-byte random value in production "
            f"(e.g. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`)."
        )
        # to stderr so it's visible even at INFO log level
        print(f"[SECURITY WARNING] {msg}", file=sys.stderr, flush=True)
        log.warning(msg)
