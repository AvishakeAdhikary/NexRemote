"""Lifecycle of the protocol listeners (wss 8765, ws 8766, UDP discovery 37020)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Iterator

import uvicorn

from nexremote_server.core.context import AppContext
from nexremote_server.core.protocol import ProtocolEndpoint
from nexremote_server.net.discovery import start_discovery

log = logging.getLogger(__name__)


class EmbeddedServer(uvicorn.Server):
    """uvicorn server that runs inside our loop and leaves signal handling to the host process."""

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


def make_config(app, host: str, port: int, **kwargs) -> uvicorn.Config:
    return uvicorn.Config(
        app,
        host=host,
        port=port,
        lifespan="off",
        log_config=None,
        access_log=False,
        ws="websockets-sansio",
        ws_max_size=32 * 1024 * 1024,
        ws_per_message_deflate=False,  # JPEG/H.264 frames do not compress; skip the CPU cost
        server_header=False,
        **kwargs,
    )


class ServerManager:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.endpoint = ProtocolEndpoint(ctx)
        self._servers: list[EmbeddedServer] = []
        self._tasks: list[asyncio.Task] = []
        self._discovery: asyncio.DatagramTransport | None = None
        self._lock = asyncio.Lock()
        self.last_error: str = ""

    @property
    def running(self) -> bool:
        return self.ctx.running

    async def start(self) -> tuple[bool, str]:
        async with self._lock:
            if self.ctx.running:
                return True, ""
            ok, reason = self.ctx.can_serve()
            if not ok:
                self.last_error = reason
                return False, reason
            s = self.ctx.settings.current
            cert = self.ctx.cert
            secure = EmbeddedServer(
                make_config(
                    self.endpoint.build_app(secure=True),
                    "0.0.0.0",
                    s.server_port,
                    ssl_certfile=str(cert.cert_path),
                    ssl_keyfile=str(cert.key_path),
                )
            )
            insecure = EmbeddedServer(
                make_config(self.endpoint.build_app(secure=False), "0.0.0.0", s.server_port_insecure)
            )
            try:
                for server in (secure, insecure):
                    task = asyncio.create_task(server.serve())
                    self._servers.append(server)
                    self._tasks.append(task)
                    await self._wait_started(server, task)
                self._discovery = await start_discovery(s.discovery_port, self.ctx.discovery_response)
                for feature in self.ctx.features:
                    await feature.start()
            except Exception as exc:
                self.last_error = f"start_failed: {exc}"
                log.error("server start failed: %s", exc)
                await self._shutdown()
                return False, self.last_error
            self.ctx.running = True
            self.last_error = ""
            self.ctx.bus.publish("server_state", {"running": True})
            log.info(
                "listening on wss:%d ws:%d udp:%d", s.server_port, s.server_port_insecure, s.discovery_port
            )
            return True, ""

    async def _wait_started(self, server: EmbeddedServer, task: asyncio.Task) -> None:
        for _ in range(200):
            if server.started:
                return
            if task.done():
                exc = task.exception() if not task.cancelled() else None
                raise RuntimeError(f"listener exited during startup: {exc or 'port in use?'}")
            await asyncio.sleep(0.025)
        raise RuntimeError("listener did not start in time")

    async def stop(self) -> None:
        async with self._lock:
            await self._shutdown()
            self.ctx.bus.publish("server_state", {"running": False})

    async def _shutdown(self) -> None:
        self.ctx.running = False
        for key, session in list(self.ctx.sessions.items()):
            self.ctx.sessions.pop(key, None)
            await self.endpoint.close_features(session)
            await session.close(1001, "Server stopped")
            self.ctx.bus.publish("session_disconnected", {"device_id": session.device_id})
        for feature in self.ctx.features:
            try:
                await feature.stop()
            except Exception:
                log.debug("feature stop failed", exc_info=True)
        if self._discovery is not None:
            self._discovery.close()
            self._discovery = None
        for server in self._servers:
            server.should_exit = True
        if self._tasks:
            done, pending = await asyncio.wait(self._tasks, timeout=5)
            for task in pending:
                task.cancel()
        self._servers.clear()
        self._tasks.clear()
        self.ctx.sessions.clear()

    async def restart(self) -> tuple[bool, str]:
        await self.stop()
        return await self.start()
