"""UDP discovery responder on port 37020."""

from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import Callable
from typing import Any

from nexremote_server.protocol.constants import DISCOVERY_MAGIC
from nexremote_server.protocol.jsonutil import dumps

log = logging.getLogger(__name__)


def is_discovery_request(payload: bytes) -> bool:
    return payload[: len(DISCOVERY_MAGIC)] == DISCOVERY_MAGIC


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, build_response: Callable[[], dict[str, Any]]) -> None:
        self._build_response = build_response
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport) -> None:  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if not is_discovery_request(data) or self.transport is None:
            return
        try:
            self.transport.sendto(dumps(self._build_response()).encode("utf-8"), addr)
        except OSError:
            log.debug("discovery reply to %s failed", addr, exc_info=True)

    def error_received(self, exc: Exception) -> None:
        # Windows reports ICMP port-unreachable for earlier replies here; ignore.
        log.debug("discovery socket error: %s", exc)


async def start_discovery(
    port: int, build_response: Callable[[], dict[str, Any]]
) -> asyncio.DatagramTransport:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", port))
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(lambda: _DiscoveryProtocol(build_response), sock=sock)
    return transport
