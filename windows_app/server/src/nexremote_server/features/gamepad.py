"""Virtual Xbox 360 controller per client via ViGEmBus (vgamepad)."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

from nexremote_server.features.base import Feature, available, unavailable
from nexremote_server.protocol.jsonutil import get_bool, get_float, get_str

log = logging.getLogger(__name__)

GAMEPAD_TYPES = ("gamepad", "gamepad_xinput", "gamepad_android", "gamepad_dinput")
GYRO_FACTOR = 0.06
_CREATE_NO_WINDOW = 0x08000000


def vigembus_installed() -> bool:
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["sc.exe", "query", "ViGEmBus"], capture_output=True, timeout=5, creationflags=_CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\ViGEmBus"):
            return True
    except OSError:
        pass
    try:
        result = subprocess.run(
            ["pnputil", "/enum-drivers"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_CREATE_NO_WINDOW,
        )
        return "vigembus" in result.stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return False


def _axis(value: float) -> float:
    return max(-1.0, min(1.0, value))


@dataclass
class _Pad:
    device: Any
    right_x: float = 0.0
    right_y: float = 0.0


class GamepadFeature(Feature):
    message_types = (*GAMEPAD_TYPES, "gamepad_mode")
    RETRY_SECONDS = 5.0
    DRIVER_CACHE_SECONDS = 30.0

    def __init__(self, ctx, input_controller) -> None:
        super().__init__(ctx)
        self.input = input_controller
        self.mode = "xinput"
        self._pads: dict[str, _Pad] = {}
        self._vg: Any = None
        self._vg_failed_at = 0.0
        self._driver_cache: tuple[float, bool] = (0.0, False)

    # availability -------------------------------------------------------------
    def driver_installed(self) -> bool:
        """Cached result; refreshed off the event loop by `refresh_driver_status`."""
        return self._driver_cache[1]

    async def refresh_driver_status(self) -> bool:
        value = await asyncio.to_thread(vigembus_installed)
        self._driver_cache = (time.monotonic(), value)
        return value

    async def start(self) -> None:
        await self.refresh_driver_status()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def stop(self) -> None:
        task = getattr(self, "_refresh_task", None)
        if task is not None:
            task.cancel()

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(self.DRIVER_CACHE_SECONDS)
            await self.refresh_driver_status()

    def _module(self) -> Any:
        if self._vg is not None:
            return self._vg
        if time.monotonic() - self._vg_failed_at < self.RETRY_SECONDS:
            return None
        try:
            import vgamepad

            self._vg = vgamepad
        except Exception:
            self._vg_failed_at = time.monotonic()
            log.info("vgamepad unavailable", exc_info=True)
        return self._vg

    @property
    def ready(self) -> bool:
        return self.driver_installed() and self._module() is not None

    def status(self) -> dict[str, Any]:
        if self.ready:
            return available("Native gamepad transport is ready.")
        if self.driver_installed():
            return unavailable(
                "ViGEmBus is installed, but the virtual controller backend is still initializing or needs the host restarted cleanly.",
                "restart_server",
            )
        return unavailable("Install ViGEmBus to enable native gamepad transport.", "install_vigem")

    # handling -----------------------------------------------------------------
    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        if msg_type == "gamepad_mode":
            self.mode = get_str(msg, "mode", self.mode) or "xinput"
            session.state["gamepad_mode"] = self.mode
            await session.send_encrypted(
                {
                    "type": "gamepad_mode",
                    "mode": self.mode,
                    "status": {"available": self.ready, "mode": self.mode},
                    "feature_status": self.ctx.feature_status(),
                }
            )
            return

        if not self._handle_hybrid(msg):
            self._apply(session.device_id, msg)
        if msg_type == "gamepad_dinput":
            self.mode = "dinput"

    def _handle_hybrid(self, msg: dict[str, Any]) -> bool:
        """Buttons named keyboard_<key> / mouse_<button> drive the keyboard and mouse instead."""
        if get_str(msg, "input_type").lower() != "button":
            return False
        button = get_str(msg, "button")
        pressed = get_bool(msg, "pressed")
        lowered = button.lower()
        if lowered.startswith("keyboard_") and button[9:].strip():
            (self.input.press_key if pressed else self.input.release_key)(button[9:])
            return True
        if lowered.startswith("mouse_") and button[6:].strip():
            (self.input.mouse_down if pressed else self.input.mouse_up)(button[6:])
            return True
        return False

    def _pad(self, device_id: str) -> _Pad | None:
        pad = self._pads.get(device_id)
        if pad is not None:
            return pad
        vg = self._module() if self.driver_installed() else None
        if vg is None:
            return None
        try:
            pad = _Pad(vg.VX360Gamepad())
        except Exception:
            log.warning("could not create virtual controller", exc_info=True)
            self._vg_failed_at = time.monotonic()
            return None
        self._pads[device_id] = pad
        return pad

    def _apply(self, device_id: str, msg: dict[str, Any]) -> None:
        pad = self._pad(device_id)
        if pad is None:
            return
        vg = self._vg
        b = vg.XUSB_BUTTON
        dev = pad.device
        try:
            match get_str(msg, "input_type").lower():
                case "button":
                    mapped = {
                        "A": b.XUSB_GAMEPAD_A, "B": b.XUSB_GAMEPAD_B, "X": b.XUSB_GAMEPAD_X, "Y": b.XUSB_GAMEPAD_Y,
                        "L1": b.XUSB_GAMEPAD_LEFT_SHOULDER, "LB": b.XUSB_GAMEPAD_LEFT_SHOULDER,
                        "R1": b.XUSB_GAMEPAD_RIGHT_SHOULDER, "RB": b.XUSB_GAMEPAD_RIGHT_SHOULDER,
                        "SELECT": b.XUSB_GAMEPAD_BACK, "BACK": b.XUSB_GAMEPAD_BACK,
                        "START": b.XUSB_GAMEPAD_START,
                        "GUIDE": b.XUSB_GAMEPAD_GUIDE, "HOME": b.XUSB_GAMEPAD_GUIDE,
                        "L3": b.XUSB_GAMEPAD_LEFT_THUMB, "R3": b.XUSB_GAMEPAD_RIGHT_THUMB,
                    }.get(get_str(msg, "button").upper())  # fmt: skip
                    if mapped is None:
                        return
                    (dev.press_button if get_bool(msg, "pressed") else dev.release_button)(button=mapped)
                case "dpad":
                    mapped = {
                        "UP": b.XUSB_GAMEPAD_DPAD_UP, "DOWN": b.XUSB_GAMEPAD_DPAD_DOWN,
                        "LEFT": b.XUSB_GAMEPAD_DPAD_LEFT, "RIGHT": b.XUSB_GAMEPAD_DPAD_RIGHT,
                    }.get(get_str(msg, "direction").upper())  # fmt: skip
                    if mapped is None:
                        return
                    (dev.press_button if get_bool(msg, "pressed") else dev.release_button)(button=mapped)
                case "joystick":
                    x, y = _axis(get_float(msg, "x")), _axis(get_float(msg, "y"))
                    if get_str(msg, "stick").lower() == "right":
                        pad.right_x, pad.right_y = x, y
                        dev.right_joystick_float(x_value_float=x, y_value_float=y)
                    else:
                        dev.left_joystick_float(x_value_float=x, y_value_float=y)
                case "trigger":
                    value = max(0.0, min(1.0, get_float(msg, "value")))
                    if get_str(msg, "trigger").upper() in ("RT", "R2"):
                        dev.right_trigger_float(value_float=value)
                    else:
                        dev.left_trigger_float(value_float=value)
                case "gyro":
                    pad.right_x = _axis(pad.right_x + get_float(msg, "x") * GYRO_FACTOR)
                    pad.right_y = _axis(pad.right_y - get_float(msg, "y") * GYRO_FACTOR)
                    dev.right_joystick_float(x_value_float=pad.right_x, y_value_float=pad.right_y)
                case _:
                    return
            dev.update()
        except Exception:
            log.warning("failed to apply gamepad input", exc_info=True)

    async def on_session_closed(self, session) -> None:
        pad = self._pads.pop(session.device_id, None)
        if pad is None:
            return
        try:
            pad.device.reset()
            pad.device.update()
        except Exception:
            log.debug("failed to reset virtual controller", exc_info=True)
        del pad  # vgamepad unplugs the target when the object is garbage-collected
