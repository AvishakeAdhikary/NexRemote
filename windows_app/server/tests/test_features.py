import asyncio
import json
import os
import socket
from pathlib import Path

from conftest import PhoneIdentity, connect, recv_json, recv_until

from nexremote_server.db.engine import SettingsStore, TrustedDeviceStore, create_db_engine
from nexremote_server.db.legacy_import import import_legacy
from nexremote_server.features.adb import parse_devices
from nexremote_server.features.files import FileExplorer
from nexremote_server.features.input import VIRTUAL_KEYS
from nexremote_server.features.phone_screen import relay_prefix, sanitize_input
from nexremote_server.features.screen import resolve_coordinate, target_size
from nexremote_server.net.discovery import start_discovery
from nexremote_server.protocol import legacy_crypto
from nexremote_server.protocol.frames import PSCR_FLAG_CONFIG, build_phone_screen


# input ---------------------------------------------------------------------------
def test_hotkey_maps_characters_and_releases_everything(ctx, backend) -> None:
    ctx.input.controller.hotkey(["ctrl", "c"])
    assert backend.calls == [
        ("key", VIRTUAL_KEYS["ctrl"], False),
        ("key", ord("C"), False),
        ("key", ord("C"), True),
        ("key", VIRTUAL_KEYS["ctrl"], True),
    ]


def test_keyboard_and_mouse_messages(ctx, backend) -> None:
    c = ctx.input.controller
    c.handle_keyboard({"type": "keyboard", "action": "type", "text": "hi"})
    c.handle_keyboard({"action": "press", "key": "enter"})
    c.handle_mouse({"action": "move_relative", "dx": 5, "dy": -3})
    c.handle_mouse({"input_action": "click", "button": "right", "count": 2})
    c.handle_mouse({"action": "scroll", "dx": 0, "dy": -2})
    assert backend.calls[:5] == [
        ("unicode", "h", False), ("unicode", "h", True), ("unicode", "i", False), ("unicode", "i", True),
        ("key", 0x0D, False),
    ]  # fmt: skip
    assert ("mouse", 0x0001, 5, -3, 0) in backend.calls
    assert backend.calls.count(("mouse", 0x0008, 0, 0, 0)) == 2  # right down x2
    assert ("mouse", 0x0800, 0, 0, -240) in backend.calls
    # 1.2 precise (smooth) scrolling: raw wheel units, not notches.
    c.handle_mouse({"action": "scroll", "dx": 0, "dy": 30, "precise": True})
    assert ("mouse", 0x0800, 0, 0, 30) in backend.calls


async def test_macro_and_hybrid_gamepad_buttons(ctx, backend, listeners) -> None:
    async with connect(listeners.insecure_url) as ws:
        await ws.send(PhoneIdentity().auth())
        await recv_json(ws)
        send = lambda m: ws.send(legacy_crypto.encrypt_to_base64(json.dumps(m)))  # noqa: E731
        await send(
            {"type": "macro", "steps": [{"action": "keyboard:a", "delay": 10}, {"action": "mouse:left"}]}
        )
        await send({"type": "gamepad", "input_type": "button", "button": "keyboard_space", "pressed": True})
        await send(
            {"type": "gamepad_dinput", "input_type": "button", "button": "mouse_right", "pressed": False}
        )
        await send({"type": "gamepad_mode", "mode": "dinput"})
        reply = await recv_until(ws, lambda m: m.get("type") == "gamepad_mode")
        assert reply["mode"] == "dinput" and reply["status"] == {"available": False, "mode": "dinput"}
        assert "feature_status" in reply
    assert ("unicode", "a", False) in backend.calls
    assert ("key", 0x20, False) in backend.calls
    assert ("mouse", 0x0010, 0, 0, 0) in backend.calls


# screen helpers --------------------------------------------------------------------
def test_target_size_never_upscales() -> None:
    assert target_size(2560, 1440, "native") == (2560, 1440)
    assert target_size(2560, 1440, "half") == (1280, 720)
    assert target_size(2560, 1440, "720p") == (1280, 720)
    assert target_size(1280, 720, "1080p") == (1280, 720)
    assert target_size(1920, 1080, "800x600") == (800, 450)
    assert target_size(1920, 1080, "garbage") == (1920, 1080)


def test_resolve_coordinate() -> None:
    assert resolve_coordinate({"normalized_x": 0.5}, "normalized_x", "x", 1920, 1920) == 1920 + 960
    assert resolve_coordinate({"normalized_x": 3}, "normalized_x", "x", 0, 100) == 99
    assert resolve_coordinate({"x": 5000}, "normalized_x", "x", 0, 100) == 99


# files ----------------------------------------------------------------------------
def test_file_explorer_round_trip(tmp_path: Path) -> None:
    fx = FileExplorer()
    root = str(tmp_path)
    assert fx.handle({"action": "create_folder", "path": root, "name": "Docs"})["action"] == "folder_created"
    assert (
        fx.handle({"action": "create_folder", "path": root, "name": "Docs"})["message"]
        == 'Folder "Docs" already exists'
    )
    created = fx.handle({"action": "create_file", "path": root, "name": "a.txt", "content": "hello"})
    assert created["action"] == "file_created"
    listing = fx.handle({"action": "list", "path": root})
    assert [f["name"] for f in listing["files"]] == ["Docs", "a.txt"]  # folders first
    assert "size" not in listing["files"][0] and listing["files"][1]["size"] == 5
    assert fx.handle({"action": "read_file", "path": created["path"]})["content"] == "hello"
    saved = fx.handle({"action": "write_file", "path": created["path"], "content": "bye"})
    assert saved == {
        "type": "file_explorer",
        "action": "file_saved",
        "path": created["path"],
        "name": "a.txt",
        "size": 3,
    }
    renamed = fx.handle({"action": "rename", "path": created["path"], "new_name": "b.txt"})
    assert renamed["new_name"] == "b.txt" and os.path.exists(renamed["new_path"])
    copied = fx.handle(
        {"action": "copy", "source": renamed["new_path"], "destination": os.path.join(root, "Docs")}
    )
    assert copied["action"] == "copied" and os.path.exists(copied["destination"])
    found = fx.handle({"action": "search", "path": root, "query": "B."})
    assert [f["name"] for f in found["files"]] == ["b.txt"]
    props = fx.handle({"action": "properties", "path": renamed["new_path"]})
    assert props["item_type"] == "file" and props["size"] == 3
    assert fx.handle({"action": "delete", "path": os.path.join(root, "Docs")})["action"] == "deleted"
    assert fx.handle({"action": "list", "path": ""})["message"] == "Invalid or restricted path"
    assert fx.handle({"action": "nope"})["message"] == "Unknown action: nope"
    drives = fx.handle({"action": "drive_list"})["drives"]
    assert drives and {"name", "path", "kind", "is_ready", "label"} == set(drives[0])


# phone screen ---------------------------------------------------------------------
def test_sanitize_input() -> None:
    assert sanitize_input({"input_action": "tap", "normalized_x": 2, "normalized_y": 0.5}) == {
        "type": "phone_screen", "action": "input", "input_action": "tap",
        "normalized_x": 1.0, "normalized_y": 0.5, "duration_ms": 50,
    }  # fmt: skip
    assert sanitize_input({"input_action": "key", "key": "HOME"})["key"] == "home"
    assert sanitize_input({"input_action": "key", "key": "power"}) is None
    assert sanitize_input({"input_action": "shell"}) is None
    assert sanitize_input({"input_action": "swipe", "duration_ms": 99999})["duration_ms"] == 5000


async def test_phone_screen_relay_and_control(ctx, listeners) -> None:
    events = ctx.bus.subscribe()
    async with connect(listeners.insecure_url) as ws:
        await ws.send(PhoneIdentity("phone-x").auth())
        await recv_json(ws)
        send = lambda m: ws.send(legacy_crypto.encrypt_to_base64(json.dumps(m)))  # noqa: E731

        # Not sharing yet: control is refused.
        assert await ctx.phone_screen.send_input("phone-x", {"input_action": "tap"}) == "not_sharing"

        await send({"type": "phone_screen", "action": "start", "codec": "h264", "width": 1080, "height": 2400,
                    "fps": 30, "rotation": 0, "control_available": False})  # fmt: skip
        frame = build_phone_screen(0, PSCR_FLAG_CONFIG, 0, b"\x00\x00\x00\x01\x67\x42")
        await ws.send(frame)

        seen_start = seen_binary = False
        while not (seen_start and seen_binary):
            kind, payload = await asyncio.wait_for(events.get(), 5)
            if kind == "json" and payload["event"] == "phone_screen_started":
                assert payload["width"] == 1080 and payload["control_available"] is False
                seen_start = True
            elif kind == "binary":
                assert payload == relay_prefix("phone-x") + frame
                seen_binary = True
        assert ctx.phone_screen.cached_config_frames() == [relay_prefix("phone-x") + frame]
        assert ctx.find_session("phone-x").describe()["phone_screen"] is True  # /state must not crash

        assert (
            await ctx.phone_screen.send_input("phone-x", {"input_action": "tap"})
            == "control_not_allowed_on_phone"
        )
        await send({"type": "phone_screen", "action": "control_changed", "control_available": True})
        await asyncio.sleep(0.2)
        ctx.settings.update(phone_control_enabled=False)
        assert (
            await ctx.phone_screen.send_input("phone-x", {"input_action": "tap"}) == "control_disabled_on_pc"
        )
        ctx.settings.update(phone_control_enabled=True)
        assert (
            await ctx.phone_screen.send_input(
                "phone-x", {"input_action": "tap", "normalized_x": 0.25, "normalized_y": 0.75}
            )
            is None
        )
        forwarded = await recv_until(ws, lambda m: m.get("type") == "phone_screen")
        assert forwarded["input_action"] == "tap" and forwarded["normalized_x"] == 0.25

        # Audio (1.2): refused until the phone says it can capture, then relayed once active.
        assert await ctx.phone_screen.request_audio("phone-x", True) == "audio_not_available_on_phone"
        await send({"type": "phone_screen", "action": "config_changed", "audio_available": True})
        await asyncio.sleep(0.2)
        assert await ctx.phone_screen.request_audio("phone-x", True) is None
        request = await recv_until(ws, lambda m: m.get("action") == "audio_request")
        assert request == {"type": "phone_screen", "action": "audio_request", "enabled": True}
        await send({"type": "phone_screen", "action": "audio_changed", "audio_active": True,
                    "sample_rate": 48000, "channels": 2})  # fmt: skip
        await asyncio.sleep(0.2)
        assert ctx.phone_screen.active_shares()[0]["audio_active"] is True
        audio = b"PAUD\x00" + (0).to_bytes(8, "big") + b"\x01\x00\x02\x00"
        await ws.send(audio)
        while True:
            kind, payload = await asyncio.wait_for(events.get(), 5)
            if kind == "binary" and payload[1 + len("phone-x") :].startswith(b"PAUD"):
                assert payload == relay_prefix("phone-x") + audio
                break

        await send({"type": "phone_screen", "action": "stop"})
        await asyncio.sleep(0.2)
        assert ctx.phone_screen.active_shares() == []


# legacy import ----------------------------------------------------------------------
def test_legacy_import_preserves_identity(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(
        json.dumps(
            {
                "SchemaVersion": 1, "PcName": "OLD-PC", "DeviceId": "11111111-2222-3333-4444-555555555555",
                "ServerPort": 8765, "RequireApproval": False, "ThemePreference": 2, "MaxClients": 3,
                "TermsOfServiceAccepted": True, "TermsOfServiceVersionAccepted": "2026-04-05",
                "TermsOfServiceAcceptedAt": "2026-04-06T10:00:00+00:00", "AuditLogging": True,
                "CameraAccessConsentGranted": True,
            }
        ),
        encoding="utf-8-sig",
    )  # fmt: skip
    (tmp_path / "trusted_devices.json").write_text(
        json.dumps(
            {
                "phone-a": {"name": "Pixel", "first_connected": 1775000000, "last_connected": "2026-05-01T00:00:00Z",
                            "public_key": "KEY-A"},
                "phone-b": {"name": "Galaxy", "public_key": ""},
            }
        )
    )  # fmt: skip
    engine = create_db_engine(tmp_path / "nexremote.db")
    settings, devices = SettingsStore(engine), TrustedDeviceStore(engine)
    assert import_legacy(tmp_path, settings, devices, fresh_db=True)
    s = settings.current
    assert (s.pc_name, s.device_id, s.require_approval, s.theme_preference, s.max_clients) == (
        "OLD-PC", "11111111-2222-3333-4444-555555555555", False, "dark", 3,
    )  # fmt: skip
    assert s.camera_access_consent_granted and s.terms_of_service_accepted_at.year == 2026
    a = devices.get("PHONE-A")  # case-insensitive like the legacy host
    assert a is not None and a.public_key == "KEY-A" and a.first_connected.year == 2026
    assert devices.get("phone-b") is not None
    assert (tmp_path / "settings.json.imported").exists()
    # Second boot: nothing to import, settings survive a reload.
    assert not import_legacy(tmp_path, settings, devices, fresh_db=False)
    assert SettingsStore(engine).current.device_id == "11111111-2222-3333-4444-555555555555"


# discovery & adb -----------------------------------------------------------------------
async def test_discovery_reply(ctx) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    transport = await start_discovery(port, ctx.discovery_response)
    try:
        loop = asyncio.get_running_loop()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.setblocking(False)
            client.sendto(b"NEXREMOTE_DISCOVER", ("127.0.0.1", port))
            data = await asyncio.wait_for(loop.sock_recv(client, 4096), 3)
    finally:
        transport.close()
    reply = json.loads(data)
    assert reply == {
        "type": "discovery_response", "name": "TEST-PC", "port": 8765, "port_insecure": 8766,
        "id": ctx.settings.current.device_id, "version": "1.0.0", "cert_fingerprint": ctx.cert.fingerprint,
    }  # fmt: skip
    assert len(ctx.cert.fingerprint.split(":")) == 32


def test_parse_adb_devices() -> None:
    out = "List of devices attached\nR58M123\tdevice\nemulator-5554\tunauthorized\n\n"
    assert parse_devices(out) == [("R58M123", "device"), ("emulator-5554", "unauthorized")]


# task manager -----------------------------------------------------------------------
def test_task_manager_snapshot_is_fast_and_excludes_idle() -> None:
    import time

    from nexremote_server.features.tasks import TaskManager

    manager = TaskManager()
    started = time.perf_counter()
    snap = manager._capture_snapshot()
    assert time.perf_counter() - started < 0.5
    pids = {p["pid"] for p in snap["processes"]}
    assert 0 not in pids and snap["processes"]
    system = snap["system"]
    assert {"cpu_usage", "memory_usage", "disk_usage", "disk_active", "net_recv_bps", "process_count"} <= set(system)
    assert all(0.0 <= p["cpu"] <= 100.0 for p in snap["processes"])
