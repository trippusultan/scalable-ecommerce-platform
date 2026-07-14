"""Guided demo: registers a user, creates a product, fills the cart, and checks
out through the API Gateway. Run AFTER `python scripts/run_local.py start`.

Prints each step so you can follow the full microservices flow.
"""
from __future__ import annotations

import sys
import time

import requests

BASE = "http://127.0.0.1:8000"


def _j(r):
    try:
        return r.status_code, r.json()
    except Exception:  # noqa: BLE001
        return r.status_code, r.text


def main() -> int:
    print("=== waiting for gateway ===")
    for _ in range(30):
        try:
            if requests.get(f"{BASE}/health", timeout=5).status_code == 200:
                break
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    else:
        print("gateway not up. Run: python scripts/run_local.py start")
        return 1

    print("\n[1] Register alice")
    sc, body = _j(requests.post(f"{BASE}/api/users/register", json={
        "username": "alice", "email": "alice@shop.dev", "password": "password123",
        "full_name": "Alice"}))
    if sc in (200, 201):
        token = body["access_token"]
        print(f"    ok -> user_id={body['user_id']}")
    elif sc == 409:
        sc, body = _j(requests.post(f"{BASE}/api/users/login",
                                    json={"username": "alice", "password": "password123"}))
        token = body["access_token"]
        print("    (already registered, used login)")
    else:
        print("    FAILED", sc, body); return 1
    h = {"Authorization": f"Bearer {token}"}

    print("\n[2] Create a product (Widget, $25, stock 3)")
    sc, body = _j(requests.post(f"{BASE}/api/products/products", json={
        "name": "Widget", "price": 25.0, "stock": 3}))
    pid = body["id"]
    print(f"    ok -> product_id={pid}")

    print("\n[3] Add 2x Widget to cart")
    sc, body = _j(requests.post(f"{BASE}/api/cart/cart/items", headers=h,
                               json={"product_id": pid, "quantity": 2}))
    print(f"    ok -> cart={body}")

    print("\n[4] Checkout (order + payment + stock reserve + notify)")
    sc, body = _j(requests.post(f"{BASE}/api/orders/checkout", headers=h))
    print(f"    status={sc} -> {body}")
    if sc != 201:
        return 1

    print("\n[5] Verify stock decremented (3 -> 1)")
    sc, body = _j(requests.get(f"{BASE}/api/products/products/{pid}"))
    print(f"    stock={body['stock']}")

    print("\n[6] Verify cart cleared")
    sc, body = _j(requests.get(f"{BASE}/api/cart/cart", headers=h))
    print(f"    cart={body}")

    print("\n[7] List orders")
    sc, body = _j(requests.get(f"{BASE}/api/orders/orders", headers=h))
    print(f"    orders={body}")

    print("\nDONE. Check .runtime/logs/notification-service.log for the order.placed email.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
