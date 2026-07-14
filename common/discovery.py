"""Service discovery client.

Services self-register with the registry on startup (heartbeat every few
seconds) and look up peer URLs by name. The registry is itself a microservice
(`discovery_service`). If the registry is unreachable, callers transparently
fall back to the static `*_SERVICE_URL` env values, so the platform still works
without the discovery service (and in native dev).

Registry REST API (see discovery_service/main.py):
  PUT    /register      {name, url, health_url?}
  PUT    /heartbeat     {name}
  GET    /services      -> {name: {url, last_seen, ...}, ...}
  GET    /services/{name} -> {name, url, ...}
  DELETE /services/{name}
"""
from __future__ import annotations

import os
import threading
from typing import Any

import httpx


class DiscoveryClient:
    def __init__(self, registry_url: str, fallback_urls: dict[str, str]) -> None:
        self.registry_url = registry_url.rstrip("/")
        self.fallback = fallback_urls
        # Cache holds ONLY registry-learned URLs. Do NOT seed it with the static
        # fallback URLs — otherwise resolve() would hit the cache and never
        # consult the registry (so services would always resolve to the static
        # default ports, ignoring registry-registered ports).
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()
        self._client = httpx.Client(base_url=self.registry_url, timeout=3.0)

    def resolve(self, name: str) -> str:
        """Return the URL for a service, preferring the registry, else env."""
        with self._lock:
            if name in self._cache:
                return self._cache[name]
        # cache miss -> try registry
        if self.registry_url:
            try:
                r = self._client.get(f"/services/{name}")
                if r.status_code == 200:
                    url = r.json().get("url")
                    if url:
                        with self._lock:
                            self._cache[name] = url
                        return url
            except Exception:  # noqa: BLE001
                pass
        return self.fallback.get(name, "")

    def register(self, name: str, url: str, health_url: str | None = None) -> bool:
        try:
            self._client.put(
                "/register",
                json={"name": name, "url": url, "health_url": health_url or f"{url}/health"},
            )
            with self._lock:
                self._cache[name] = url
            return True
        except Exception:  # noqa: BLE001
            return False

    def heartbeat(self, name: str) -> bool:
        try:
            self._client.put(f"/heartbeat", json={"name": name})
            return True
        except Exception:  # noqa: BLE001
            return False

    def deregister(self, name: str) -> None:
        try:
            self._client.delete(f"/services/{name}")
        except Exception:  # noqa: BLE001
            pass

    @property
    def using_registry(self) -> bool:
        return bool(self.registry_url)
