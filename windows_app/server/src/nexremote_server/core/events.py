"""In-process event bus feeding the control API's /events WebSocket."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)


class EventBus:
    """Fan-out of JSON events and binary payloads to UI subscribers.

    Each subscriber has a bounded queue. Binary payloads (video) are dropped when a
    subscriber falls behind; JSON events are never dropped silently, the oldest is evicted.
    """

    def __init__(self, maxsize: int = 256) -> None:
        self._subscribers: set[asyncio.Queue[tuple[str, Any]]] = set()
        self._maxsize = maxsize

    def subscribe(self) -> asyncio.Queue[tuple[str, Any]]:
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue(self._maxsize)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[tuple[str, Any]]) -> None:
        self._subscribers.discard(queue)

    @property
    def has_subscribers(self) -> bool:
        return bool(self._subscribers)

    def publish(self, event: str, data: dict[str, Any] | None = None) -> None:
        item = ("json", {"event": event, **(data or {})})
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(item)

    def publish_binary(self, payload: bytes) -> None:
        for queue in list(self._subscribers):
            if not queue.full():
                queue.put_nowait(("binary", payload))
