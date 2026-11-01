"""A connected, authenticated client."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any, Protocol

from starlette.websockets import WebSocket, WebSocketState

from nexremote_server.protocol.jsonutil import dumps

log = logging.getLogger(__name__)


class MessageCipher(Protocol):
    name: str

    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, payload: str) -> str: ...


@dataclass(eq=False)
class ClientSession:
    websocket: WebSocket
    device_id: str
    device_name: str
    platform: str
    secure: bool
    cipher: MessageCipher
    remote_address: str = ""
    client_version: str = ""
    state: dict[str, Any] = field(default_factory=dict)  # per-feature scratch state
    _send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _tasks: dict[str, asyncio.Task[Any]] = field(default_factory=dict)
    closed: bool = False

    @property
    def is_open(self) -> bool:
        return not self.closed and self.websocket.client_state == WebSocketState.CONNECTED

    async def send_text(self, text: str) -> None:
        if not self.is_open:
            return
        async with self._send_lock:
            try:
                await self.websocket.send_text(text)
            except Exception:  # peer went away mid-send
                log.debug("send_text failed for %s", self.device_id, exc_info=True)

    async def send_plain(self, payload: dict[str, Any]) -> None:
        await self.send_text(dumps(payload))

    async def send_encrypted(self, payload: dict[str, Any]) -> None:
        if not self.is_open:
            return
        # Encrypt inside the lock so v2 nonce counters match frame order on the wire.
        async with self._send_lock:
            try:
                await self.websocket.send_text(self.cipher.encrypt(dumps(payload)))
            except Exception:
                log.debug("send_encrypted failed for %s", self.device_id, exc_info=True)

    async def send_binary(self, payload: bytes, *, droppable: bool = True) -> bool:
        """Send a stream frame. Droppable frames are skipped when a send is in flight."""
        if not self.is_open:
            return False
        if droppable and self._send_lock.locked():
            return False
        async with self._send_lock:
            try:
                await self.websocket.send_bytes(payload)
                return True
            except Exception:
                return False

    def run_task(self, name: str, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        """Start a named background task, replacing (and cancelling) any task with that name."""
        self.cancel_task(name)
        task = asyncio.create_task(coro, name=f"{self.device_id}:{name}")
        self._tasks[name] = task

        def _done(t: asyncio.Task[Any]) -> None:
            if self._tasks.get(name) is t:
                self._tasks.pop(name, None)
            if not t.cancelled() and t.exception() is not None:
                log.debug("task %s ended with error", name, exc_info=t.exception())

        task.add_done_callback(_done)
        return task

    def cancel_task(self, name: str) -> None:
        task = self._tasks.pop(name, None)
        if task is not None and not task.done():
            task.cancel()

    def task_names(self, prefix: str = "") -> list[str]:
        return [n for n, t in self._tasks.items() if n.startswith(prefix) and not t.done()]

    def has_task(self, name: str) -> bool:
        task = self._tasks.get(name)
        return task is not None and not task.done()

    def cancel_all(self) -> None:
        for name in list(self._tasks):
            self.cancel_task(name)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.cancel_all()
        if self.websocket.client_state == WebSocketState.CONNECTED:
            with contextlib.suppress(Exception):
                await self.websocket.close(code=code, reason=reason)
        self.closed = True

    def describe(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "platform": self.platform,
            "secure": self.secure,
            "crypto": self.cipher.name,
            "remote_address": self.remote_address,
            "client_version": self.client_version,
            "phone_screen": bool(getattr(self.state.get("phone_screen"), "active", False)),
        }
