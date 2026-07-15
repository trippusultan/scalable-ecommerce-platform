#!/usr/bin/env python3
"""All-in-one container entrypoint for single-host deploys (Render/Railway).

Runs the whole platform inside ONE container: the 6 backend services on internal
localhost ports plus the gateway on $PORT (public). No service-discovery registry
is needed because every service is reachable at 127.0.0.1 — the gateway resolves
peers via the static *_SERVICE_URL env vars (see common/config.service_urls()).

This is the pragmatic free-tier topology: one cold start, localhost-fast internal
calls, no cross-service discovery timeouts. For a true multi-host microservice
deploy, use render.yaml (one Render service per component) instead.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DATA_DIR", "/tmp/ecom-data"))
DATA.mkdir(parents=True, exist_ok=True)

PUBLIC_PORT = int(os.environ.get("PORT", "8000"))

# internal ports for the backend services (localhost only)
INTERNAL = {
    "user-service": 8101,
    "product-service": 8102,
    "cart-service": 8103,
    "payment-service": 8104,
    "order-service": 8105,
    "notification-service": 8106,
}
MODULE = {
    "user-service": "user_service.main",
    "product-service": "product_service.main",
    "cart-service": "cart_service.main",
    "payment-service": "payment_service.main",
    "order-service": "order_service.main",
    "notification-service": "notification_service.main",
    "gateway": "gateway.main",
}

# static peer URLs so the gateway (and services) resolve each other on localhost
PEER_ENV = {
    "USER_SERVICE_URL": f"http://127.0.0.1:{INTERNAL['user-service']}",
    "PRODUCT_SERVICE_URL": f"http://127.0.0.1:{INTERNAL['product-service']}",
    "CART_SERVICE_URL": f"http://127.0.0.1:{INTERNAL['cart-service']}",
    "PAYMENT_SERVICE_URL": f"http://127.0.0.1:{INTERNAL['payment-service']}",
    "ORDER_SERVICE_URL": f"http://127.0.0.1:{INTERNAL['order-service']}",
    "NOTIFICATION_SERVICE_URL": f"http://127.0.0.1:{INTERNAL['notification-service']}",
}

procs: list[subprocess.Popen] = []


def _base_env(service_name: str, port: int) -> dict:
    env = dict(os.environ)
    env.update(PEER_ENV)
    env["SERVICE_NAME"] = service_name
    env["PORT"] = str(port)
    env["EVENT_BUS"] = os.environ.get("EVENT_BUS", "memory")  # no rabbitmq in-container
    env["DATABASE_URL"] = f"sqlite:///{(DATA / (service_name + '.db')).as_posix()}"
    # no discovery registry: force static resolution
    env.pop("DISCOVERY_URL", None)
    return env


def _spawn(service_name: str, module: str, port: int) -> None:
    env = _base_env(service_name, port)
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", f"{module}:app",
         "--host", "0.0.0.0", "--port", str(port)],
        cwd=str(ROOT), env=env,
    )
    procs.append(p)
    print(f"[entrypoint] started {service_name} on :{port} (pid {p.pid})", flush=True)


def _wait(url: str, timeout: int = 90) -> bool:
    import requests
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=3).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _seed() -> None:
    import requests
    env = dict(os.environ)
    env["SEED_BASE"] = f"http://127.0.0.1:{PUBLIC_PORT}"
    try:
        subprocess.run([sys.executable, "scripts/seed.py"], cwd=str(ROOT), env=env, timeout=120)
    except Exception as e:
        print(f"[entrypoint] seed skipped/failed: {e}", flush=True)


def _shutdown(*_a) -> None:
    print("[entrypoint] shutting down...", flush=True)
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)


def main() -> int:
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # 1) backend services on internal ports
    for name, port in INTERNAL.items():
        _spawn(name, MODULE[name], port)

    # 2) wait for backends to be healthy
    for name, port in INTERNAL.items():
        ok = _wait(f"http://127.0.0.1:{port}/health")
        print(f"[entrypoint] {name} healthy={ok}", flush=True)

    # 3) gateway on the public $PORT
    _spawn("gateway", MODULE["gateway"], PUBLIC_PORT)
    gw_ok = _wait(f"http://127.0.0.1:{PUBLIC_PORT}/health")
    print(f"[entrypoint] gateway healthy={gw_ok} on :{PUBLIC_PORT}", flush=True)

    # 4) seed real sample data (idempotent — skips existing)
    _seed()
    print("[entrypoint] ALL UP", flush=True)

    # 5) supervise: if any process dies, exit so the platform restarts the container
    while True:
        for p in procs:
            code = p.poll()
            if code is not None:
                print(f"[entrypoint] a service exited (code {code}); shutting down for restart", flush=True)
                _shutdown()
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
