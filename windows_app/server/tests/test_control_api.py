import asyncio

import httpx
import pytest

from nexremote_server.api.control import create_control_app
from nexremote_server.core.server import ServerManager

TOKEN = "secret-token"


@pytest.fixture
def api(ctx):
    app = create_control_app(ctx, ServerManager(ctx), TOKEN, asyncio.Event())
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1")


async def test_token_required(api) -> None:
    async with api:
        assert (await api.get("/health")).status_code == 200
        assert (await api.get("/state")).status_code == 401
        assert (await api.get("/state", headers={"Authorization": "Bearer wrong"})).status_code == 401
        state = (await api.get("/state", headers={"Authorization": f"Bearer {TOKEN}"})).json()
        assert state["pc_name"] == "TEST-PC"
        assert state["qr_payload"]["cert_fingerprint"] == state["cert_fingerprint"]
        assert state["legal"]["accepted"] is True


async def test_settings_patch_rules(api, ctx) -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with api:
        r = await api.patch("/settings", json={"pc_name": "Desk", "max_clients": 2}, headers=headers)
        assert r.status_code == 200 and r.json()["pc_name"] == "Desk"
        assert ctx.settings.current.max_clients == 2
        r = await api.patch("/settings", json={"device_id": "hijack"}, headers=headers)
        assert r.status_code == 400
        r = await api.patch("/settings", json={"theme_preference": "neon"}, headers=headers)
        assert r.status_code == 400


async def test_consent_and_devices(api, ctx) -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    ctx.trusted.record_connection("dev-1", "Pixel", "KEY")
    async with api:
        state = (await api.post("/consent", json={"camera": True}, headers=headers)).json()
        assert state["consent"]["camera"] is True
        assert state["feature_status"]["camera"]["available"] is True
        devices = (await api.get("/devices", headers=headers)).json()
        assert devices[0]["device_id"] == "dev-1" and devices[0]["has_key"] is True
        assert (await api.delete("/devices/dev-1", headers=headers)).json() == {"ok": True}
        assert (await api.get("/devices", headers=headers)).json() == []
        assert (await api.post("/approvals/nobody", json={"approved": True}, headers=headers)).json() == {
            "ok": False
        }
