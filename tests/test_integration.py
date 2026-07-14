"""Live integration test: boots all 7 microservices as real uvicorn processes,
then drives the full e-commerce flow through the API Gateway over HTTP.

This is the faithful distributed-systems test (each service runs in its own
process with its own SQLite DB + the in-memory event bus).

Run:  pytest tests/test_integration.py -q
"""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
# Unique temp dir per run so a previous run's orphaned subprocesses (which hold
# a Windows file lock on the SQLite files) can never block a new run.
DATA = Path(tempfile.mkdtemp(prefix="ecom_test_"))
SERVICES = {
    "user-service": 8101,
    "product-service": 8102,
    "cart-service": 8103,
    "payment-service": 8104,
    "order-service": 8105,
    "notification-service": 8106,
    "discovery-service": 8109,
    "gateway": 8100,
}


def _kill_by_ports(ports) -> None:
    """Best-effort: terminate any process still listening on the given ports."""
    try:
        import psutil
    except Exception:
        return
    listening = {}
    for c in psutil.net_connections(kind="tcp"):
        if c.status == "LISTEN" and c.laddr.port in ports and c.pid:
            listening[c.laddr.port] = c.pid
    for pid in listening.values():
        try:
            psutil.Process(pid).kill()
        except Exception:  # noqa: BLE001
            pass


def _wait_health(url: str, timeout: float = 5.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            if requests.get(url, timeout=timeout).status_code == 200:
                return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def cluster():
    (ROOT / "tests" / "logs").mkdir(parents=True, exist_ok=True)
    # Clear any orphaned processes from a previous (failed) run still holding our
    # test ports — otherwise the new uvicorn procs can't bind and never come up.
    _kill_by_ports(list(SERVICES.values()))
    time.sleep(0.5)
    env = dict(os.environ)
    env.update({
        "EVENT_BUS": "memory",
        "JWT_SECRET": "test-secret",
        "DATA_DIR": str(DATA),
        "LOG_LEVEL": "WARNING",
        # point the gateway (and services) at the test's own discovery service so
        # upstreams resolve to the 8100-range ports, not the default 8000 range.
        "DISCOVERY_URL": f"http://127.0.0.1:{SERVICES['discovery-service']}",
    })
    procs = []
    for svc, port in SERVICES.items():
        env["SERVICE_NAME"] = svc
        env["PORT"] = str(port)
        # Use forward slashes so SQLAlchemy parses the Windows path reliably
        # (tempfile.mkdtemp returns backslashes, which break sqlite:/// URLs).
        env["DATABASE_URL"] = f"sqlite:///{DATA.as_posix()}/{svc}.db"
        module = "gateway.main" if svc == "gateway" else f"{svc.replace('-', '_')}.main"
        cmd = [sys.executable, "-m", "uvicorn", f"{module}:app", "--host", "127.0.0.1",
               "--port", str(port), "--log-level", "info"]
        logf = open(ROOT / "tests" / "logs" / f"{svc}.log", "w")
        p = subprocess.Popen(cmd, cwd=str(ROOT), env=env,
                              stdout=logf, stderr=subprocess.STDOUT)
        procs.append(p)
        time.sleep(0.4)  # stagger cold starts so they don't all contend at once

    # wait for all health endpoints
    health_results = {}
    for svc, port in SERVICES.items():
        health_results[svc] = _wait_health(f"http://127.0.0.1:{port}/health")
    ok = all(health_results.values())
    if not ok:
        print("[FIXTURE] unhealthy services:",
              {k: v for k, v in health_results.items() if not v}, file=sys.stderr, flush=True)
    assert ok, "not all services became healthy"
    yield f"http://127.0.0.1:{SERVICES['gateway']}"
    for p in procs:
        try:
            p.send_signal(signal.SIGTERM)
        except Exception:  # noqa: BLE001
            p.kill()
    for p in procs:
        try:
            p.wait(timeout=5)
        except Exception:  # noqa: BLE001
            p.kill()
    # safety net: kill anything still bound to our ports (Windows leaves orphans)
    _kill_by_ports(list(SERVICES.values()))
    # Windows releases file locks lazily; retry the cleanup a few times.
    for _ in range(10):
        try:
            shutil.rmtree(DATA, ignore_errors=True)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.3)


def _register(base: str) -> str:
    r = requests.post(f"{base}/api/users/register", timeout=10, json={
        "username": "alice", "email": "alice@x.com", "password": "password123"})
    if r.status_code == 409:
        r = requests.post(f"{base}/api/users/login", timeout=10,
                          json={"username": "alice", "password": "password123"})
    assert r.status_code in (200, 201), r.text
    return r.json()["access_token"]


def test_end_to_end_through_gateway(cluster):
    base = cluster
    token = _register(base)
    h = {"Authorization": f"Bearer {token}"}

    # create product
    p = requests.post(f"{base}/api/products/products", timeout=10, json={
        "name": "Gadget", "price": 25.0, "stock": 3}).json()
    pid = p["id"]

    # add to cart
    c = requests.post(f"{base}/api/cart/cart/items", headers=h, timeout=10,
                      json={"product_id": pid, "quantity": 2})
    assert c.status_code == 201

    # checkout
    co = requests.post(f"{base}/api/orders/checkout", headers=h, timeout=15)
    assert co.status_code == 201, co.text
    body = co.json()
    assert body["status"] == "confirmed"
    assert body["payment_status"] == "succeeded"
    assert body["total"] == 50.0

    # stock decremented
    stock = requests.get(f"{base}/api/products/products/{pid}", timeout=10).json()["stock"]
    assert stock == 1

    # cart cleared
    cart = requests.get(f"{base}/api/cart/cart", headers=h, timeout=10).json()
    assert cart == []

    # order retrievable
    orders = requests.get(f"{base}/api/orders/orders", headers=h, timeout=10).json()
    assert any(o["id"] == body["order_id"] for o in orders)


def test_gateway_health_aggregation(cluster):
    h = requests.get(f"{cluster}/health", timeout=10).json()
    assert h["gateway"] == "ok"
    assert set(h["services"].keys()) == {
        "users", "products", "cart", "orders", "payments", "notify"}


def test_unauthorized_rejected(cluster):
    r = requests.get(f"{cluster}/api/cart/cart", timeout=10)
    assert r.status_code == 401
