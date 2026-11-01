"""USB mode: keeps `adb reverse tcp:<insecure> tcp:<insecure>` active for attached phones."""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from nexremote_server.features.base import Feature, available, unavailable

log = logging.getLogger(__name__)

POLL_SECONDS = 5.0
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


@dataclass(frozen=True, slots=True)
class AdbStatus:
    tool_available: bool = False
    tool_path: str = ""
    device_detected: bool = False
    device_authorized: bool = False
    reverse_active: bool = False
    state: str = "unavailable"
    reason: str = "ADB platform-tools are not available."


def parse_devices(output: str) -> list[tuple[str, str]]:
    devices = []
    for line in output.splitlines()[1:]:
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))
    return devices


class AdbBridgeFeature(Feature):
    message_types = ()

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.status_info = AdbStatus()
        self._task: asyncio.Task | None = None

    def resolve_adb(self) -> str:
        app_dir = Path(sys.executable).resolve().parent
        for candidate in (
            self.ctx.config.tools_dir / "platform-tools" / "adb.exe",
            app_dir / "platform-tools" / "adb.exe",
            app_dir / "tools" / "platform-tools" / "adb.exe",
        ):
            if candidate.exists():
                return str(candidate)
        return shutil.which("adb") or ""

    def status(self) -> dict:
        s = self.status_info
        if not s.tool_available:
            return unavailable(
                "ADB platform-tools are not bundled or installed yet.", "install_platform_tools"
            )
        if s.reverse_active:
            return available(s.reason)
        return unavailable(s.reason, "connect_device" if s.device_authorized else "authorize_device")

    async def _run(self, *args: str) -> str:
        def call() -> str:
            try:
                result = subprocess.run(
                    list(args), capture_output=True, text=True, timeout=15, creationflags=_CREATE_NO_WINDOW
                )
                return (result.stdout or "") + (result.stderr or "")
            except (OSError, subprocess.SubprocessError) as exc:
                return f"error: {exc}"

        return await asyncio.to_thread(call)

    async def poll_once(self) -> AdbStatus:
        tool = self.resolve_adb()
        if not tool:
            return AdbStatus()
        await self._run(tool, "start-server")
        devices = parse_devices(await self._run(tool, "devices"))
        authorized = [serial for serial, state in devices if state == "device"]
        unauthorized = any(state == "unauthorized" for _, state in devices)
        port = str(self.ctx.settings.current.server_port_insecure)
        reverse = False
        for serial in authorized:
            out = await self._run(tool, "-s", serial, "reverse", f"tcp:{port}", f"tcp:{port}")
            reverse |= "error" not in out.lower()
        if reverse:
            state, reason = "reverse_active", "ADB reverse is active for an attached device."
        elif unauthorized:
            state, reason = (
                "device_unauthorized",
                "USB debugging is connected, but the device still needs RSA authorization.",
            )
        elif devices:
            state, reason = "device_detected", "ADB sees a device, but reverse is not active yet."
        else:
            state, reason = "idle", "ADB is ready. Connect a device with USB debugging to enable USB mode."
        return AdbStatus(True, tool, bool(devices), bool(authorized), reverse, state, reason)

    async def _loop(self) -> None:
        while True:
            try:
                status = await self.poll_once()
            except Exception:
                log.debug("adb poll failed", exc_info=True)
                status = AdbStatus()
            if status != self.status_info:
                self.status_info = status
                self.ctx.publish_status()
            await asyncio.sleep(POLL_SECONDS)

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
        self.status_info = AdbStatus()
