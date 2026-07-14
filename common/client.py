"""Thin async HTTP client for service-to-service calls (uses httpx).

All requests carry the forwarded JWT so downstream services can authorize.
Failures raise ServiceError with the upstream status for clean 502s.

If a DiscoveryClient is supplied, the target URL is resolved through the
service registry on every call (so services are found by name regardless of
the port they actually listen on); otherwise the static base_url is used.
"""
from __future__ import annotations

import httpx
from typing import Any

from .errors import ServiceError


class ServiceClient:
    def __init__(
        self,
        base_url: str,
        *,
        discovery: "DiscoveryClient | None" = None,
        service_name: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.static_url = base_url.rstrip("/")
        self.discovery = discovery
        self.service_name = service_name
        self._client = httpx.AsyncClient(timeout=timeout)

    def _resolve(self) -> str:
        if self.discovery and self.service_name:
            resolved = self.discovery.resolve(self.service_name)
            if resolved:
                return resolved.rstrip("/")
        return self.static_url

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self, method: str, path: str, *, token: str | None = None, **kwargs: Any
    ) -> Any:
        base = self._resolve()
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = await self._client.request(
                method, f"{base}{path}", headers=headers, **kwargs
            )
        except httpx.HTTPError as e:
            raise ServiceError(f"{base} unreachable: {e}") from e
        if resp.status_code >= 400:
            raise ServiceError(
                f"{base}{path} -> {resp.status_code}: {resp.text[:300]}"
            )
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def get(self, path: str, **kw: Any) -> Any:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> Any:
        return await self.request("POST", path, **kw)

    async def patch(self, path: str, **kw: Any) -> Any:
        return await self.request("PATCH", path, **kw)

    async def delete(self, path: str, **kw: Any) -> Any:
        return await self.request("DELETE", path, **kw)


# Local import to avoid a circular import at module load time.
from .discovery import DiscoveryClient  # noqa: E402
