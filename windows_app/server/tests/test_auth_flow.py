"""End-to-end handshake tests against real listeners (wss with the generated cert, and ws)."""

import asyncio
import json

from conftest import PhoneIdentity, connect, recv_json, recv_until

from nexremote_server.protocol import legacy_crypto, v2_crypto


async def _secure_login(url: str, phone: PhoneIdentity, raw_signature: bool = False, **auth_extra):
    ws = await connect(url).__aenter__()
    await ws.send(phone.auth(**auth_extra))
    challenge = await recv_json(ws)
    assert challenge["type"] == "auth_challenge"
    await ws.send(
        json.dumps(
            {
                "type": "auth_response",
                "device_id": phone.device_id,
                "signature": phone.sign(challenge["nonce"], raw_signature),
            }
        )
    )
    return ws, challenge, await recv_json(ws)


async def test_insecure_auth_then_legacy_command(ctx, listeners, phone) -> None:
    async with connect(listeners.insecure_url) as ws:
        await ws.send(phone.auth())
        success = await recv_json(ws)
        assert success["type"] == "auth_success"
        assert success["server_name"] == "TEST-PC"
        assert "protocol_version" not in success  # v1 clients get the v1 shape
        assert set(success["capabilities"]) >= {
            "keyboard", "mouse", "gamepad", "gamepad_available", "gamepad_mode", "gamepad_modes",
            "screen_streaming", "screen_audio_streaming", "camera_streaming", "file_transfer",
            "clipboard", "multi_display",
        }  # fmt: skip
        assert set(success["feature_status"]["camera"]) == {
            "supported",
            "available",
            "reason",
            "action_required",
        }

        await ws.send(
            legacy_crypto.encrypt_to_base64(json.dumps({"type": "task_manager", "action": "system_info"}))
        )
        raw = await asyncio.wait_for(ws.recv(), 10)
        reply = json.loads(legacy_crypto.decrypt_from_base64(raw))  # replies are encrypted
        assert reply["type"] == "task_manager" and reply["action"] == "system_info"
        assert {"cpu_usage", "memory_usage", "disk_usage", "memory_total", "memory_available"} <= set(reply)

        await ws.send(json.dumps({"type": "ping"}))
        assert await recv_json(ws, decrypt=lambda _: "{}") == {"type": "pong"}

    assert ctx.trusted.get(phone.device_id) is not None


async def test_auth_accepts_legacy_encrypted_auth_payload(listeners, phone) -> None:
    async with connect(listeners.insecure_url) as ws:
        await ws.send(legacy_crypto.encrypt_to_base64(phone.auth()))
        assert (await recv_json(ws))["type"] == "auth_success"


async def test_secure_challenge_with_der_and_raw_signatures(listeners) -> None:
    for raw in (False, True):
        phone = PhoneIdentity(device_id=f"dev-{raw}")
        ws, challenge, result = await _secure_login(listeners.secure_url, phone, raw)
        assert challenge["server_name"] == "TEST-PC" and "capabilities" in challenge
        assert result["type"] == "auth_success"
        await ws.close()


async def test_secure_rejects_bad_signature(listeners, phone) -> None:
    async with connect(listeners.secure_url) as ws:
        await ws.send(phone.auth())
        challenge = await recv_json(ws)
        await ws.send(
            json.dumps(
                {
                    "type": "auth_response",
                    "device_id": phone.device_id,
                    "signature": PhoneIdentity().sign(challenge["nonce"]),
                }
            )
        )
        assert (await recv_json(ws))["type"] == "auth_failed"


async def test_secure_rejects_changed_key_for_trusted_device(ctx, listeners, phone) -> None:
    ctx.trusted.record_connection(phone.device_id, phone.name, PhoneIdentity().public_key_b64)
    async with connect(listeners.secure_url) as ws:
        await ws.send(phone.auth())
        assert (await recv_json(ws))["type"] == "auth_failed"


async def test_secure_requires_public_key(listeners) -> None:
    async with connect(listeners.secure_url) as ws:
        await ws.send(json.dumps({"type": "auth", "device_id": "x", "device_name": "y"}))
        assert (await recv_json(ws))["type"] == "auth_failed"


async def test_unparseable_auth_fails(listeners) -> None:
    async with connect(listeners.insecure_url) as ws:
        await ws.send("not json")
        assert (await recv_json(ws, decrypt=lambda _: "{}"))["type"] == "auth_failed"


async def test_approval_flow(ctx, listeners) -> None:
    ctx.settings.update(require_approval=True)
    events = ctx.bus.subscribe()

    async def answer(approved: bool) -> None:
        while True:
            kind, payload = await events.get()
            if kind == "json" and payload["event"] == "approval_requested":
                ctx.approvals.complete(payload["device_id"], approved)
                return

    denied = PhoneIdentity("denied-phone")
    async with connect(listeners.insecure_url) as ws:
        responder = asyncio.create_task(answer(False))
        await ws.send(denied.auth())
        assert (await recv_json(ws, timeout=15))["type"] == "connection_rejected"
        await responder
    assert ctx.trusted.get("denied-phone") is None

    approved = PhoneIdentity("approved-phone")
    async with connect(listeners.insecure_url) as ws:
        responder = asyncio.create_task(answer(True))
        await ws.send(approved.auth())
        assert (await recv_json(ws, timeout=15))["type"] == "auth_success"
        await responder

    # Trusted now, so no second approval is needed.
    async with connect(listeners.insecure_url) as ws:
        await ws.send(approved.auth())
        assert (await recv_json(ws, timeout=3))["type"] == "auth_success"


async def test_rejections(ctx, listeners) -> None:
    ctx.settings.update(max_clients=1)
    async with connect(listeners.insecure_url) as first:
        await first.send(PhoneIdentity("a").auth())
        assert (await recv_json(first))["type"] == "auth_success"
        async with connect(listeners.insecure_url) as second:
            await second.send(PhoneIdentity("b").auth())
            assert (await recv_json(second))["type"] == "connection_rejected"
        # The same device reconnecting replaces its old session instead of being rejected.
        async with connect(listeners.insecure_url) as again:
            await again.send(PhoneIdentity("a").auth())
            assert (await recv_json(again))["type"] == "auth_success"

    ctx.settings.update(enable_remote_access=False)
    async with connect(listeners.insecure_url) as ws:
        await ws.send(PhoneIdentity("c").auth())
        assert (await recv_json(ws))["type"] == "connection_rejected"


async def test_v2_negotiation_and_encrypted_commands(ctx, listeners) -> None:
    phone = PhoneIdentity("v2-phone")
    private, public = v2_crypto.generate_ephemeral()
    ws, _challenge, success = await _secure_login(
        listeners.secure_url, phone, protocol_version=2, client_ephemeral_key=public
    )
    try:
        assert success["type"] == "auth_success"
        assert success["protocol_version"] == 2
        assert success["session_crypto"] == "aes-256-gcm"
        cipher = v2_crypto.SessionCipher.for_client(
            *v2_crypto.derive_keys(private, public, success["server_ephemeral_key"])
        )

        # Plaintext commands are ignored on a v2 session; ping still works in plaintext.
        await ws.send(json.dumps({"type": "task_manager", "action": "system_info"}))
        await ws.send(json.dumps({"type": "ping"}))
        assert await recv_json(ws) == {"type": "pong"}

        await ws.send(cipher.encrypt(json.dumps({"type": "task_manager", "action": "system_info"})))
        reply = await recv_until(
            ws, lambda m: m.get("type") == "task_manager", timeout=10, decrypt=cipher.decrypt
        )
        assert reply["action"] == "system_info"
        assert ctx.find_session("v2-phone").cipher.name == "v2"
    finally:
        await ws.close()
