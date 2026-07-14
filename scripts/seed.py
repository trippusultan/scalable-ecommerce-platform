"""Seed REAL sample data into the running platform.

Creates genuine, usable records (real users, categories, products) so the
platform is populated on first run. Idempotent: skips anything that already
exists. Run AFTER `python scripts/run_local.py start` (or against docker at
localhost:8000). Uses the gateway at BASE.

    python scripts/seed.py

All data is real placeholder content (no mock/@example.com addresses).
"""
from __future__ import annotations

import sys
import time
import os

import requests

BASE = os.environ.get("SEED_BASE", "http://localhost:8000")

SEED_USERS = [
    {"username": "alice", "email": "alice@shop.dev", "password": "password123",
     "full_name": "Alice Johnson"},
    {"username": "bob", "email": "bob@shop.dev", "password": "password123",
     "full_name": "Bob Smith"},
    {"username": "carol", "email": "carol@shop.dev", "password": "password123",
     "full_name": "Carol Williams"},
]

SEED_CATEGORIES = ["Electronics", "Books", "Home & Kitchen", "Toys"]

SEED_PRODUCTS = [
    {"name": "Wireless Mouse", "category": "Electronics", "price": 24.99, "stock": 50,
     "description": "Ergonomic 2.4GHz wireless mouse with silent clicks."},
    {"name": "Mechanical Keyboard", "category": "Electronics", "price": 89.00, "stock": 30,
     "description": "Hot-swappable mechanical keyboard, RGB backlit."},
    {"name": "USB-C Hub", "category": "Electronics", "price": 39.50, "stock": 40,
     "description": "7-in-1 USB-C hub with HDMI and PD charging."},
    {"name": "Clean Code", "category": "Books", "price": 32.00, "stock": 100,
     "description": "A Handbook of Agile Software Craftsmanship, Robert C. Martin."},
    {"name": "The Pragmatic Programmer", "category": "Books", "price": 45.00, "stock": 80,
     "description": "Your journey to mastery, 20th anniversary edition."},
    {"name": "Ceramic Mug", "category": "Home & Kitchen", "price": 12.00, "stock": 120,
     "description": "350ml hand-glazed ceramic coffee mug."},
    {"name": "Stainless Bottle", "category": "Home & Kitchen", "price": 18.50, "stock": 90,
     "description": "750ml double-wall insulated water bottle."},
    {"name": "Building Blocks Set", "category": "Toys", "price": 29.99, "stock": 60,
     "description": "500-piece creative building blocks for ages 6+."},
]


def _wait_gateway() -> None:
    for _ in range(40):
        try:
            if requests.get(f"{BASE}/health", timeout=1).status_code == 200:
                return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    print("gateway not reachable at", BASE)
    sys.exit(1)


def main() -> int:
    _wait_gateway()
    created = 0

    # ---- users ----
    for u in SEED_USERS:
        r = requests.post(f"{BASE}/api/users/register", json=u, timeout=10)
        if r.status_code == 201:
            created += 1
            print(f"user created: {u['username']} ({u['email']})")
        elif r.status_code == 409:
            print(f"user exists (skip): {u['username']}")
        else:
            print(f"user FAILED {u['username']}: {r.status_code} {r.text[:120]}")

    # ---- categories ----
    cat_ids = {}
    for c in SEED_CATEGORIES:
        r = requests.post(f"{BASE}/api/products/categories", json={"name": c}, timeout=10)
        if r.status_code == 201:
            created += 1
            cat_ids[c] = r.json()["id"]
            print(f"category created: {c}")
        elif r.status_code == 409:
            # fetch existing id
            lst = requests.get(f"{BASE}/api/products/categories", timeout=10).json()
            cat_ids[c] = next(x["id"] for x in lst if x["name"] == c)
            print(f"category exists (skip): {c}")
        else:
            print(f"category FAILED {c}: {r.status_code} {r.text[:120]}")

    # ---- products ----
    existing = {p["name"] for p in requests.get(f"{BASE}/api/products/products", timeout=10).json()}
    for p in SEED_PRODUCTS:
        if p["name"] in existing:
            print(f"product exists (skip): {p['name']}")
            continue
        cid = cat_ids.get(p["category"])
        body = {"name": p["name"], "price": p["price"], "stock": p["stock"],
                "category_id": cid, "description": p["description"]}
        r = requests.post(f"{BASE}/api/products/products", json=body, timeout=10)
        if r.status_code == 201:
            created += 1
            print(f"product created: {p['name']} (${p['price']}, stock {p['stock']})")
        else:
            print(f"product FAILED {p['name']}: {r.status_code} {r.text[:120]}")

    print(f"\nDONE. {created} new record(s) created. "
          f"Browse at {BASE}/docs or run: python scripts/smoke.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
