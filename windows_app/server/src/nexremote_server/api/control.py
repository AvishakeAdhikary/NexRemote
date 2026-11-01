"""Local control API for the desktop UI. Binds to 127.0.0.1 only and requires a bearer token."""

from __future__ import annotations

import asyncio
import dataclasses
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from nexremote_server import __version__
from nexremote_server.core.context import AppContext
from nexremote_server.core.server import ServerManager
from nexremote_server.db.models import USER_EDITABLE_SETTINGS
from nexremote_server.net.lan import all_lan_ips, primary_lan_ip
from nexremote_server.protocol.constants import LEGAL_DOCUMENT_VERSION
from nexremote_server.protocol.jsonutil import get_bool

log = logging.getLogger(__name__)

# Settings that only take effect when the listeners restart.
RESTART_KEYS = frozenset({"server_port", "server_port_insecure", "discovery_port"})


def create_control_app(
    ctx: AppContext, manager: ServerManager, token: str | None, shutdown: asyncio.Event
) -> FastAPI:
    app = FastAPI(title="NexRemote control", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^(app://[a-z0-9.-]+|http://(localhost|127\.0\.0\.1):\d+)$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def check_token(supplied: str | None) -> bool:
        return token is None or (supplied is not None and hmac.compare_digest(supplied, token))

    async def require_token(request: Request) -> None:
        header = request.headers.get("authorization", "")
        supplied = header[7:] if header.lower().startswith("bearer ") else None
        if not check_token(supplied):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")

    auth = [Depends(require_token)]

    # helpers ------------------------------------------------------------------
    def settings_view() -> dict[str, Any]:
        return ctx.settings.current.model_dump(mode="json")

    def state() -> dict[str, Any]:
        s = ctx.settings.current
        lan = primary_lan_ip()
        can, reason = ctx.can_serve()
        return {
            "version": __version__,
            "running": ctx.running,
            "can_serve": can,
            "blocked_reason": reason,
            "last_error": manager.last_error,
            "pc_name": s.pc_name,
            "device_id": s.device_id,
            "ports": {
                "secure": s.server_port,
                "insecure": s.server_port_insecure,
                "discovery": s.discovery_port,
            },
            "lan_ip": lan,
            "lan_ips": all_lan_ips(),
            "qr_payload": ctx.qr_payload(lan),
            "cert_fingerprint": ctx.cert.fingerprint,
            "legal": {
                "required_version": LEGAL_DOCUMENT_VERSION,
                "accepted": s.legal_current(LEGAL_DOCUMENT_VERSION),
            },
            "consent": {
                "remote_control": s.remote_control_consent_granted,
                "background": s.background_consent_granted,
                "camera": s.camera_access_consent_granted,
            },
            "sessions": [x.describe() for x in ctx.sessions.values()],
            "approvals": ctx.approvals.pending(),
            "capabilities": ctx.capabilities(),
            "feature_status": ctx.feature_status(),
            "phone_shares": ctx.phone_screen.active_shares(),
            "adb": dataclasses.asdict(ctx.adb.status_info),
            "data_dir": str(ctx.config.data_dir),
        }

    async def apply_gating() -> None:
        can, _ = ctx.can_serve()
        if can and not ctx.running:
            await manager.start()
        elif not can and ctx.running:
            await manager.stop()

    # routes ---------------------------------------------------------------------
    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "version": __version__}

    @app.get("/state", dependencies=auth)
    async def get_state() -> dict[str, Any]:
        return state()

    @app.post("/server/start", dependencies=auth)
    async def server_start() -> dict[str, Any]:
        ok, reason = await manager.start()
        return {"ok": ok, "reason": reason, "running": ctx.running}

    @app.post("/server/stop", dependencies=auth)
    async def server_stop() -> dict[str, Any]:
        await manager.stop()
        return {"ok": True, "running": ctx.running}

    @app.post("/server/restart", dependencies=auth)
    async def server_restart() -> dict[str, Any]:
        ok, reason = await manager.restart()
        return {"ok": ok, "reason": reason, "running": ctx.running}

    @app.get("/settings", dependencies=auth)
    async def get_settings() -> dict[str, Any]:
        return settings_view()

    @app.patch("/settings", dependencies=auth)
    async def patch_settings(changes: dict[str, Any] = Body(...)) -> dict[str, Any]:
        unknown = set(changes) - USER_EDITABLE_SETTINGS
        if unknown:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"not editable: {sorted(unknown)}")
        try:
            ctx.settings.update(**changes)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        if "enable_remote_access" in changes:
            await apply_gating()
        if RESTART_KEYS & set(changes) and ctx.running:
            await manager.restart()
        ctx.publish_status()
        ctx.bus.publish("settings_changed", settings_view())
        return settings_view()

    @app.post("/legal/accept", dependencies=auth)
    async def accept_legal() -> dict[str, Any]:
        now = datetime.now(UTC)
        ctx.settings.update(
            terms_of_service_accepted=True,
            terms_of_service_accepted_at=now,
            terms_of_service_version_accepted=LEGAL_DOCUMENT_VERSION,
            terms_and_conditions_accepted=True,
            terms_and_conditions_accepted_at=now,
            terms_and_conditions_version_accepted=LEGAL_DOCUMENT_VERSION,
            privacy_policy_accepted=True,
            privacy_policy_accepted_at=now,
            privacy_policy_version_accepted=LEGAL_DOCUMENT_VERSION,
        )
        await apply_gating()
        return state()

    @app.post("/consent", dependencies=auth)
    async def set_consent(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        for key, field in (
            ("remote_control", "remote_control_consent_granted"),
            ("background", "background_consent_granted"),
            ("camera", "camera_access_consent_granted"),
        ):
            if isinstance(body.get(key), bool):
                changes[field] = body[key]
        if changes:
            ctx.settings.update(**changes)
        await apply_gating()
        ctx.publish_status()
        return state()

    @app.get("/devices", dependencies=auth)
    async def devices() -> list[dict[str, Any]]:
        connected = set(ctx.sessions)
        return [
            {
                "device_id": d.device_id,
                "name": d.name,
                "platform": d.platform,
                "first_connected": d.first_connected.isoformat(),
                "last_connected": d.last_connected.isoformat(),
                "has_key": bool(d.public_key),
                "connected": d.device_id.lower() in connected,
            }
            for d in ctx.trusted.all()
        ]

    @app.delete("/devices/{device_id}", dependencies=auth)
    async def forget_device(device_id: str) -> dict[str, Any]:
        removed = ctx.trusted.remove(device_id)
        session = ctx.find_session(device_id)
        if session is not None:
            await session.close(1000, "Device removed on PC")
        return {"ok": removed}

    @app.post("/sessions/{device_id}/disconnect", dependencies=auth)
    async def disconnect(device_id: str) -> dict[str, Any]:
        session = ctx.find_session(device_id)
        if session is None:
            return {"ok": False}
        await session.close(1000, "Disconnected by server")
        return {"ok": True}

    @app.get("/approvals", dependencies=auth)
    async def approvals() -> list[dict[str, Any]]:
        return ctx.approvals.pending()

    @app.post("/approvals/{device_id}", dependencies=auth)
    async def answer_approval(device_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
        return {"ok": ctx.approvals.complete(device_id, get_bool(body, "approved"))}

    @app.get("/events/log", dependencies=auth)
    async def event_log(limit: int = 100) -> list[dict[str, Any]]:
        return [e.model_dump(mode="json") for e in ctx.events.recent(max(1, min(limit, 500)))]

    @app.get("/phone/shares", dependencies=auth)
    async def phone_shares() -> list[dict[str, Any]]:
        return ctx.phone_screen.active_shares()

    @app.post("/phone/{device_id}/input", dependencies=auth)
    async def phone_input(device_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
        error = await ctx.phone_screen.send_input(device_id, body)
        return {"ok": error is None, "error": error}

    @app.post("/phone/{device_id}/keyframe", dependencies=auth)
    async def phone_keyframe(device_id: str) -> dict[str, Any]:
        error = await ctx.phone_screen.request_keyframe(device_id)
        return {"ok": error is None, "error": error}

    @app.post("/phone/{device_id}/stop", dependencies=auth)
    async def phone_stop(device_id: str) -> dict[str, Any]:
        error = await ctx.phone_screen.stop_share(device_id)
        return {"ok": error is None, "error": error}

    @app.post("/shutdown", dependencies=auth)
    async def request_shutdown() -> dict[str, Any]:
        shutdown.set()
        return {"ok": True}

    @app.websocket("/events")
    async def events(ws: WebSocket) -> None:
        if not check_token(ws.query_params.get("token")):
            await ws.close(code=4401)
            return
        await ws.accept()
        queue = ctx.bus.subscribe()
        try:
            await ws.send_json({"event": "hello", "state": state()})
            for frame in ctx.phone_screen.cached_config_frames():
                await ws.send_bytes(frame)
            for share in ctx.phone_screen.active_shares():
                await ctx.phone_screen.request_keyframe(share["device_id"])
            receiver = asyncio.create_task(_drain(ws))
            try:
                while not receiver.done():
                    getter = asyncio.create_task(queue.get())
                    done, _ = await asyncio.wait({getter, receiver}, return_when=asyncio.FIRST_COMPLETED)
                    if getter not in done:
                        getter.cancel()
                        break
                    kind, payload = getter.result()
                    if kind == "binary":
                        await ws.send_bytes(payload)
                    else:
                        await ws.send_json(payload)
            finally:
                receiver.cancel()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            ctx.bus.unsubscribe(queue)

    return app


async def _drain(ws: WebSocket) -> None:
    """Consume (and ignore) client messages so a disconnect is noticed promptly."""
    while True:
        message = await ws.receive()
        if message.get("type") == "websocket.disconnect":
            return
