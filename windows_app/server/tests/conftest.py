from __future__ import annotations

import asyncio
import base64
import json
import ssl
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import websockets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from nexremote_server.config import Config
from nexremote_server.core.context import AppContext
from nexremote_server.core.protocol import ProtocolEndpoint
from nexremote_server.core.server import EmbeddedServer, make_config
from nexremote_server.db.engine import EventLog, SettingsStore, TrustedDeviceStore, create_db_engine
from nexremote_server.features.input import InputBackend, InputController
from nexremote_server.net.certs import ensure_certificate
from nexremote_server.protocol import legacy_crypto
from nexremote_server.protocol.constants import LEGAL_DOCUMENT_VERSION


class RecordingBackend(InputBackend):
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def key(self, vk: int, up: bool) -> None:
        self.calls.append(("key", vk, up))

    def unicode(self, ch: str, up: bool) -> None:
        self.calls.append(("unicode", ch, up))

    def char_vk(self, ch: str) -> int | None:
        return ord(ch.upper()) if ch.isalnum() else None

    def mouse(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
        self.calls.append(("mouse", flags, dx, dy, data))


@pytest.fixture
def backend() -> RecordingBackend:
    return RecordingBackend()


@pytest.fixture
def ctx(tmp_path: Path, backend: RecordingBackend) -> AppContext:
    config = Config(data_dir=tmp_path, dev=True)
    config.ensure_dirs()
    engine = create_db_engine(config.db_path)
    settings = SettingsStore(engine)
    settings.update(
        terms_of_service_accepted=True,
        terms_of_service_version_accepted=LEGAL_DOCUMENT_VERSION,
        terms_and_conditions_accepted=True,
        terms_and_conditions_version_accepted=LEGAL_DOCUMENT_VERSION,
        privacy_policy_accepted=True,
        privacy_policy_version_accepted=LEGAL_DOCUMENT_VERSION,
        remote_control_consent_granted=True,
        require_approval=False,
        pc_name="TEST-PC",
    )
    cert = ensure_certificate(config.certs_dir)
    context = AppContext(
        config, settings, TrustedDeviceStore(engine), EventLog(engine), cert, InputController(backend)
    )
    # Keep tests away from real drivers / audio devices.
    context.screen._audio_status = (False, "test")
    context.gamepad._driver_cache = (0.0, False)
    return context


@dataclass
class Listeners:
    secure_url: str
    insecure_url: str


async def _serve(app, **kwargs) -> tuple[EmbeddedServer, asyncio.Task, int]:
    server = EmbeddedServer(make_config(app, "127.0.0.1", 0, **kwargs))
    task = asyncio.create_task(server.serve())
    while not server.started:
        if task.done():
            raise RuntimeError(task.exception())
        await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    return server, task, port


@pytest.fixture
async def listeners(ctx: AppContext) -> AsyncIterator[Listeners]:
    endpoint = ProtocolEndpoint(ctx)
    secure, secure_task, secure_port = await _serve(
        endpoint.build_app(True), ssl_certfile=str(ctx.cert.cert_path), ssl_keyfile=str(ctx.cert.key_path)
    )
    insecure, insecure_task, insecure_port = await _serve(endpoint.build_app(False))
    ctx.running = True
    yield Listeners(f"wss://127.0.0.1:{secure_port}/", f"ws://127.0.0.1:{insecure_port}/")
    for session in list(ctx.sessions.values()):
        await session.close()
    secure.should_exit = insecure.should_exit = True
    await asyncio.wait({secure_task, insecure_task}, timeout=5)


def client_ssl() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def connect(url: str):
    return websockets.connect(url, ssl=client_ssl() if url.startswith("wss") else None, compression=None)


class PhoneIdentity:
    """A client keypair like the Android app's AndroidKeyStore identity."""

    def __init__(self, device_id: str = "phone-1", name: str = "Pixel Test") -> None:
        self.device_id = device_id
        self.name = name
        self.key = ec.generate_private_key(ec.SECP256R1())

    @property
    def public_key_b64(self) -> str:
        der = self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(der).decode()

    def auth(self, **extra: Any) -> str:
        return json.dumps(
            {
                "type": "auth",
                "device_id": self.device_id,
                "device_name": self.name,
                "client_public_key": self.public_key_b64,
                "client_version": "1.0.1",
                "platform": "android",
                **extra,
            }
        )

    def sign(self, nonce_b64: str, raw: bool = False) -> str:
        der = self.key.sign(base64.b64decode(nonce_b64), ec.ECDSA(hashes.SHA256()))
        if raw:
            from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

            r, s = decode_dss_signature(der)
            der = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        return base64.b64encode(der).decode()


@pytest.fixture
def phone() -> PhoneIdentity:
    return PhoneIdentity()


async def recv_json(ws, timeout: float = 5.0, decrypt=legacy_crypto.decrypt_from_base64) -> dict[str, Any]:
    raw = await asyncio.wait_for(ws.recv(), timeout)
    assert isinstance(raw, str)
    try:
        return json.loads(raw)
    except ValueError:
        return json.loads(decrypt(raw))


async def recv_until(ws, predicate, timeout: float = 5.0, decrypt=legacy_crypto.decrypt_from_base64):
    """Receive text frames until one matches; binary frames and media_info pushes are skipped."""
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        raw = await asyncio.wait_for(ws.recv(), max(0.01, remaining))
        if isinstance(raw, bytes):
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            msg = json.loads(decrypt(raw))
        if predicate(msg):
            return msg
