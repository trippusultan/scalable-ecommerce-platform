"""Event bus — decouples services (e.g. Order emits 'order.placed', the
Notification service reacts). Two backends:
  - "memory":  in-process pub/sub (dev / single container without a broker)
  - "rabbitmq": real broker via pika (production; lazy import so the dep is optional)

In native multi-process mode (no broker) publishers also fire-and-forget POST
the event to the Notification Service's /rpc/event endpoint, so events are still
delivered across processes without a message broker.

Emitted events are also logged (JSON) so the ELK stack picks them up.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Callable

_log = logging.getLogger("events")

_HANDLERS: dict[str, list[Callable[[dict], None]]] = {}
_local = threading.Lock()


class EventBus:
    def __init__(self, backend: str = "memory", url: str | None = None) -> None:
        self.backend = backend
        self.url = url
        self._conn = None
        if backend == "rabbitmq":
            self._ensure_broker()

    def _ensure_broker(self) -> None:
        import pika  # optional dependency

        params = pika.URLParameters(self.url or "amqp://guest:guest@localhost:5672/")
        self._conn = pika.BlockingConnection(params)
        ch = self._conn.channel()
        ch.exchange_declare(exchange="ecommerce", exchange_type="topic", durable=True)
        self._channel = ch

    def publish(self, name: str, payload: dict[str, Any]) -> None:
        event = {"event": name, "payload": payload}
        _log.info("EVENT %s %s", name, json.dumps(payload, default=str))
        if self.backend == "rabbitmq":
            self._channel.basic_publish(
                exchange="ecommerce",
                routing_key=name,
                body=json.dumps(event).encode(),
            )
        else:
            with _local:
                for handler in list(_HANDLERS.get(name, [])):
                    try:
                        handler(event)
                    except Exception as e:  # noqa: BLE001
                        _log.error("event handler failed for %s: %s", name, e)
            # Cross-process delivery (native multi-service run, no broker):
            # fire-and-forget POST to the Notification Service's RPC endpoint.
            url = os.environ.get("NOTIFICATION_SERVICE_URL")
            if url:
                threading.Thread(
                    target=_http_deliver, args=(url, event), daemon=True
                ).start()

    def subscribe(self, name: str, handler: Callable[[dict], None]) -> None:
        if self.backend == "rabbitmq":
            self._channel.queue_declare(queue=name, durable=True)
            self._channel.queue_bind(exchange="ecommerce", queue=name, routing_key=name)
            self._channel.basic_consume(
                queue=name,
                on_message_callback=lambda ch, m, props, body: handler(
                    json.loads(body.decode())
                ),
                auto_ack=True,
            )
            self._channel.start_consuming()
        else:
            with _local:
                _HANDLERS.setdefault(name, []).append(handler)


def _http_deliver(base_url: str, event: dict) -> None:
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/rpc/event",
            data=json.dumps(event).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:  # noqa: BLE001
        _log.warning("event http delivery failed: %s", e)


_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        backend = os.environ.get("EVENT_BUS", "memory")
        _bus = EventBus(backend=backend, url=os.environ.get("RABBITMQ_URL"))
    return _bus


def publish(name: str, payload: dict[str, Any]) -> None:
    get_bus().publish(name, payload)
