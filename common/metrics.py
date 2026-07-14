"""Minimal Prometheus metrics (no external dependency).

Each service imports `metrics` and mounts `metrics.endpoint` at `/metrics`,
and adds `MetricsMiddleware` to track HTTP requests/latency. Exports are
scraped by Prometheus in docker-compose. Works without any extra packages.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class _Counter:
    def __init__(self) -> None:
        self.value = 0

    def inc(self, by: float = 1) -> None:
        self.value += by


class _Histogram:
    """Bucketed histogram (powers-of-2-ish buckets in seconds)."""

    _BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf"))

    def __init__(self) -> None:
        self.count = 0
        self.sum = 0.0
        self.buckets = [0] * len(self._BUCKETS)

    def observe(self, v: float) -> None:
        self.count += 1
        self.sum += v
        for i, b in enumerate(self._BUCKETS):
            if v <= b:
                self.buckets[i] += 1
                break


class Metrics:
    def __init__(self, namespace: str) -> None:
        self.ns = namespace
        self.request_count = _Counter()
        self.request_latency = _Histogram()
        self.error_count = _Counter()
        self._lock = __import__("threading").Lock()

    def observe_request(self, method: str, path: str, status: int, latency: float) -> None:
        with self._lock:
            self.request_count.inc()
            self.request_latency.observe(latency)
            if status >= 500:
                self.error_count.inc()

    def render(self) -> str:
        lines: list[str] = []
        name = f"{self.ns}_http_requests_total"
        lines.append(f"# HELP {name} Total HTTP requests.")
        lines.append(f"# TYPE {name} counter")
        with self._lock:
            lines.append(f"{name} {self.request_count.value}")
            lines.append(f"# HELP {self.ns}_http_request_errors_total Total 5xx responses.")
            lines.append(f"# TYPE {self.ns}_http_request_errors_total counter")
            lines.append(f"{self.ns}_http_request_errors_total {self.error_count.value}")
            lines.append(f"# HELP {self.ns}_http_request_duration_seconds Request latency.")
            lines.append(f"# TYPE {self.ns}_http_request_duration_seconds histogram")
            cumulative = 0
            for b, c in zip(self.request_latency._BUCKETS, self.request_latency.buckets):
                cumulative += c
                le = "+Inf" if b == float("inf") else repr(b)
                lines.append(f"{self.ns}_http_request_duration_seconds_bucket{{le=\"{le}\"}} {cumulative}")
            lines.append(
                f"{self.ns}_http_request_duration_seconds_sum {self.request_latency.sum}")
            lines.append(
                f"{self.ns}_http_request_duration_seconds_count {self.request_latency.count}")
        return "\n".join(lines) + "\n"


_REGISTRY: dict[str, Metrics] = {}


def get_metrics(namespace: str) -> Metrics:
    if namespace not in _REGISTRY:
        _REGISTRY[namespace] = Metrics(namespace)
    return _REGISTRY[namespace]


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics: Metrics) -> None:
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency = time.perf_counter() - start
        # collapse path params to avoid cardinality blow-up
        path = request.url.path
        if path.startswith("/api/"):
            path = "/api/<svc>/<path>"
        self.metrics.observe_request(request.method, path, response.status_code, latency)
        return response
