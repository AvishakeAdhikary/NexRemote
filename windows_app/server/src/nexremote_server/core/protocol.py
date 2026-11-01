"""WebSocket protocol endpoint: authentication handshake and message loop.

Mirrors the WinUI host's RemoteServerHost.Protocol.cs behaviour, plus negotiated v2 crypto.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import secrets
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from fastapi import FastAPI, WebSocket
from fastapi.responses import PlainTextResponse
from starlette.websockets import WebSocketDisconnect

from nexremote_server.core.context import AppContext
from nexremote_server.core.session import ClientSession
from nexremote_server.protocol import constants as c
from nexremote_server.protocol import legacy_crypto, v2_crypto
from nexremote_server.protocol.frames import parse_frame
from nexremote_server.protocol.jsonutil import dumps, get_int, get_str, try_parse_object

log = logging.getLogger(__name__)


# helpers ----------------------------------------------------------------------
async def _receive(ws: WebSocket, timeout: float | None) -> dict[str, Any] | None:
    try:
        message = await asyncio.wait_for(ws.receive(), timeout) if timeout else await ws.receive()
    except (TimeoutError, WebSocketDisconnect, RuntimeError):
        return None
    if message.get("type") == "websocket.disconnect":
        return None
    return message


async def _receive_text(ws: WebSocket, timeout: float) -> str | None:
    message = await _receive(ws, timeout)
    if message is None:
        return None
    if message.get("text") is not None:
        return message["text"]
    raw = message.get("bytes")
    return raw.decode("utf-8", errors="replace") if raw is not None else None


def _parse_maybe_legacy(text: str) -> dict[str, Any] | None:
    """Plain JSON first, then legacy-encrypted Base64 (both accepted during auth)."""
    parsed = try_parse_object(text)
    if parsed is not None:
        return parsed
    try:
        return try_parse_object(legacy_crypto.decrypt_from_base64(text))
    except Exception:
        return None


def parse_auth(text: str) -> dict[str, Any] | None:
    msg = _parse_maybe_legacy(text)
    if msg is None or get_str(msg, "type").lower() != c.AUTH:
        return None
    if not get_str(msg, "device_id").strip() or not get_str(msg, "device_name").strip():
        return None
    return msg


def parse_auth_response(text: str) -> dict[str, Any] | None:
    msg = _parse_maybe_legacy(text)
    if msg is None or get_str(msg, "type").lower() != c.AUTH_RESPONSE:
        return None
    if not get_str(msg, "device_id").strip() or not get_str(msg, "signature").strip():
        return None
    return msg


def verify_signature(public_key_b64: str, nonce_b64: str, signature_b64: str) -> bool:
    """ECDSA-SHA256 over the raw nonce bytes; accepts DER or raw r||s (IEEE P1363) signatures."""
    if not public_key_b64 or not nonce_b64 or not signature_b64:
        return False
    try:
        key = serialization.load_der_public_key(base64.b64decode(public_key_b64))
        if not isinstance(key, ec.EllipticCurvePublicKey):
            return False
        nonce = base64.b64decode(nonce_b64)
        signature = base64.b64decode(signature_b64)
    except Exception:
        return False
    candidates = [signature]
    size = (key.curve.key_size + 7) // 8
    if len(signature) == 2 * size:
        r = int.from_bytes(signature[:size], "big")
        s = int.from_bytes(signature[size:], "big")
        candidates.append(encode_dss_signature(r, s))
    for candidate in candidates:
        try:
            key.verify(candidate, nonce, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError):
            continue
    return False


# endpoint -----------------------------------------------------------------------
class ProtocolEndpoint:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    def build_app(self, secure: bool) -> FastAPI:
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

        @app.get("/")
        async def root() -> PlainTextResponse:
            return PlainTextResponse("NexRemote")

        @app.websocket("/")
        async def ws_root(websocket: WebSocket) -> None:
            await self.handle(websocket, secure)

        @app.websocket("/{path:path}")
        async def ws_any(websocket: WebSocket, path: str) -> None:
            await self.handle(websocket, secure)

        return app

    async def handle(self, ws: WebSocket, secure: bool) -> None:
        await ws.accept()
        session: ClientSession | None = None
        try:
            session = await self._handshake(ws, secure)
            if session is not None:
                await self._message_loop(session)
        except Exception:
            log.debug("client session ended with error", exc_info=True)
        finally:
            if session is not None:
                await self._teardown(session)
            else:
                try:
                    await ws.close()
                except Exception:
                    pass

    async def _reject(
        self, ws: WebSocket, kind: str, device_id: str = "", name: str = "", detail: str = ""
    ) -> None:
        try:
            await ws.send_text(dumps({"type": kind}))
        except Exception:
            pass
        self.ctx.events.add(device_id=device_id, device_name=name, event=kind, detail=detail)
        self.ctx.bus.publish(
            "connection_rejected", {"device_id": device_id, "device_name": name, "reason": detail}
        )

    async def _handshake(self, ws: WebSocket, secure: bool) -> ClientSession | None:
        ctx = self.ctx
        settings = ctx.settings.current
        remote = f"{ws.client.host}:{ws.client.port}" if ws.client else ""

        text = await _receive_text(ws, c.AUTH_TIMEOUT_SECONDS)
        if not text or not text.strip():
            return None
        auth = parse_auth(text)
        if auth is None:
            await self._reject(ws, c.AUTH_FAILED, detail="unparseable auth")
            return None

        device_id = get_str(auth, "device_id")
        device_name = get_str(auth, "device_name")
        platform = get_str(auth, "platform")
        offered_key = get_str(auth, "client_public_key")
        trusted = ctx.trusted.get(device_id)
        stored_key = trusted.public_key if trusted is not None else ""
        public_key = stored_key or offered_key

        if not settings.enable_remote_access:
            await self._reject(ws, c.CONNECTION_REJECTED, device_id, device_name, "remote access disabled")
            return None
        if (
            settings.max_clients > 0
            and device_id.lower() not in ctx.sessions
            and len(ctx.sessions) >= settings.max_clients
        ):
            await self._reject(ws, c.CONNECTION_REJECTED, device_id, device_name, "server at capacity")
            return None

        if secure:
            if not public_key:
                await self._reject(ws, c.AUTH_FAILED, device_id, device_name, "no public key")
                return None
            if trusted is not None and stored_key and offered_key and stored_key != offered_key:
                await self._reject(ws, c.AUTH_FAILED, device_id, device_name, "public key changed")
                return None
            nonce = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
            await ws.send_text(
                dumps(
                    {
                        "type": c.AUTH_CHALLENGE,
                        "server_name": settings.pc_name,
                        "nonce": nonce,
                        "capabilities": ctx.capabilities(),
                        "feature_status": ctx.feature_status(),
                    }
                )
            )
            reply_text = await _receive_text(ws, c.AUTH_RESPONSE_TIMEOUT_SECONDS)
            reply = parse_auth_response(reply_text or "")
            if (
                reply is None
                or get_str(reply, "device_id").lower() != device_id.lower()
                or not verify_signature(public_key, nonce, get_str(reply, "signature"))
            ):
                await self._reject(ws, c.AUTH_FAILED, device_id, device_name, "pairing proof failed")
                return None

        if trusted is None and settings.require_approval:
            approved = await ctx.approvals.request(
                device_id, device_name, platform, remote, c.APPROVAL_TIMEOUT_SECONDS
            )
            ctx.events.add(
                device_id=device_id, device_name=device_name, event="approved" if approved else "denied"
            )
            if not approved:
                await self._reject(
                    ws, c.CONNECTION_REJECTED, device_id, device_name, "approval denied or timed out"
                )
                return None

        ctx.trusted.record_connection(device_id, device_name, public_key, platform)

        success: dict[str, Any] = {
            "type": c.AUTH_SUCCESS,
            "server_name": settings.pc_name,
            "capabilities": ctx.capabilities(),
            "feature_status": ctx.feature_status(),
        }
        cipher: Any = legacy_crypto.LegacyCipher()
        client_ephemeral = get_str(auth, "client_ephemeral_key")
        if get_int(auth, "protocol_version", 1) >= c.NEGOTIATED_PROTOCOL_VERSION and client_ephemeral:
            try:
                private, server_ephemeral = v2_crypto.generate_ephemeral()
                k_c2s, k_s2c = v2_crypto.derive_keys(private, client_ephemeral, server_ephemeral)
                cipher = v2_crypto.SessionCipher.for_server(k_c2s, k_s2c)
                success.update(
                    protocol_version=c.NEGOTIATED_PROTOCOL_VERSION,
                    server_ephemeral_key=server_ephemeral,
                    session_crypto=v2_crypto.SESSION_CRYPTO,
                )
            except Exception:
                log.info("v2 negotiation failed for %s; staying on legacy crypto", device_id, exc_info=True)
                cipher = legacy_crypto.LegacyCipher()

        session = ClientSession(
            websocket=ws,
            device_id=device_id,
            device_name=device_name,
            platform=platform,
            secure=secure,
            cipher=cipher,
            remote_address=remote,
            client_version=get_str(auth, "client_version"),
        )
        existing = ctx.sessions.pop(device_id.lower(), None)
        if existing is not None:
            await self.close_features(existing)
            await existing.close(1000, "Replaced by a new connection")
        ctx.sessions[device_id.lower()] = session

        await session.send_plain(success)
        ctx.events.add(
            device_id=device_id,
            device_name=device_name,
            event="connected",
            transport="secure" if secure else "insecure",
            detail=cipher.name,
        )
        ctx.bus.publish("session_connected", session.describe())
        log.info(
            "accepted %s (%s) via %s, crypto=%s",
            device_name,
            device_id,
            "wss" if secure else "ws",
            cipher.name,
        )
        return session

    def _decode_inbound(self, session: ClientSession, text: str) -> dict[str, Any] | None:
        plain = try_parse_object(text)
        if plain is not None:
            # v2 sessions accept plaintext only for keep-alive; legacy accepted anything.
            if session.cipher.name == "v2" and get_str(plain, "type").lower() not in (c.PING, c.PONG):
                return None
            return plain
        try:
            return try_parse_object(session.cipher.decrypt(text))
        except Exception:
            return None

    async def _message_loop(self, session: ClientSession) -> None:
        ws = session.websocket
        while session.is_open:
            message = await _receive(ws, None)
            if message is None:
                break
            raw = message.get("bytes")
            if raw is not None and message.get("text") is None:
                await self._dispatch_binary(session, raw)
                continue
            text = message.get("text")
            if text is None:
                continue
            msg = self._decode_inbound(session, text)
            if msg is None:
                continue
            msg_type = get_str(msg, "type").lower()
            if msg_type == c.PING:
                await session.send_plain({"type": c.PONG})
                continue
            if msg_type in (c.AUTH, c.AUTH_RESPONSE, c.PONG):
                continue
            feature = self.ctx.routes.get(msg_type)
            if feature is None:
                log.debug("unknown message type %s", msg_type)
                continue
            try:
                await feature.handle(session, msg_type, msg)
            except Exception:
                log.warning("handler for %s failed", msg_type, exc_info=True)

    async def _dispatch_binary(self, session: ClientSession, data: bytes) -> None:
        parsed = parse_frame(data)
        if parsed is None:
            return
        tag = parsed[0]
        for feature in self.ctx.features:
            try:
                if await feature.handle_binary(session, tag, data):
                    return
            except Exception:
                log.debug("binary handler failed", exc_info=True)

    async def close_features(self, session: ClientSession) -> None:
        session.cancel_all()
        for feature in self.ctx.features:
            try:
                await feature.on_session_closed(session)
            except Exception:
                log.debug("on_session_closed failed", exc_info=True)

    async def _teardown(self, session: ClientSession) -> None:
        if self.ctx.sessions.get(session.device_id.lower()) is session:
            del self.ctx.sessions[session.device_id.lower()]
            await self.close_features(session)
            self.ctx.events.add(
                device_id=session.device_id, device_name=session.device_name, event="disconnected"
            )
            self.ctx.bus.publish("session_disconnected", {"device_id": session.device_id})
        await session.close()
