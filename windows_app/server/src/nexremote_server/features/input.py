"""Keyboard, mouse and macro input via Win32 SendInput."""

from __future__ import annotations

import asyncio
import ctypes
import sys
from ctypes import wintypes
from typing import Any

from nexremote_server.features.base import Feature
from nexremote_server.protocol.jsonutil import get_int, get_str, get_str_list

VIRTUAL_KEYS: dict[str, int] = {
    "enter": 0x0D, "return": 0x0D, "backspace": 0x08, "tab": 0x09, "space": 0x20,
    "esc": 0x1B, "escape": 0x1B, "shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12,
    "cmd": 0x5B, "win": 0x5B, "caps_lock": 0x14, "delete": 0x2E, "end": 0x23, "home": 0x24,
    "page_up": 0x21, "page_down": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
}  # fmt: skip

WHEEL_DELTA = 120

_INPUT_MOUSE = 0
_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002
_KEYEVENTF_UNICODE = 0x0004
_MOUSEEVENTF_MOVE = 0x0001
_MOUSEEVENTF_LEFTDOWN, _MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
_MOUSEEVENTF_RIGHTDOWN, _MOUSEEVENTF_RIGHTUP = 0x0008, 0x0010
_MOUSEEVENTF_MIDDLEDOWN, _MOUSEEVENTF_MIDDLEUP = 0x0020, 0x0040
_MOUSEEVENTF_XDOWN, _MOUSEEVENTF_XUP = 0x0080, 0x0100
_MOUSEEVENTF_WHEEL, _MOUSEEVENTF_HWHEEL = 0x0800, 0x1000
_MOUSEEVENTF_VIRTUALDESK = 0x4000
_MOUSEEVENTF_ABSOLUTE = 0x8000


def mouse_flags(button: str) -> tuple[int, int, int]:
    """(down_flag, up_flag, mouse_data) for a button name; unknown names mean left."""
    match button.lower():
        case "right":
            return _MOUSEEVENTF_RIGHTDOWN, _MOUSEEVENTF_RIGHTUP, 0
        case "middle":
            return _MOUSEEVENTF_MIDDLEDOWN, _MOUSEEVENTF_MIDDLEUP, 0
        case "x1":
            return _MOUSEEVENTF_XDOWN, _MOUSEEVENTF_XUP, 1
        case "x2":
            return _MOUSEEVENTF_XDOWN, _MOUSEEVENTF_XUP, 2
        case _:
            return _MOUSEEVENTF_LEFTDOWN, _MOUSEEVENTF_LEFTUP, 0


class InputBackend:
    """Abstract input sink. The Win32 implementation is used in production; tests record calls."""

    def key(self, vk: int, up: bool) -> None: ...
    def unicode(self, ch: str, up: bool) -> None: ...
    def char_vk(self, ch: str) -> int | None: ...
    def mouse(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None: ...
    def virtual_screen(self) -> tuple[int, int, int, int]:
        return 0, 0, 1920, 1080


if sys.platform == "win32":

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t),
        ]  # fmt: skip

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t),
        ]  # fmt: skip

    class _HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)
    _user32.SendInput.restype = wintypes.UINT
    _user32.VkKeyScanW.argtypes = (wintypes.WCHAR,)
    _user32.VkKeyScanW.restype = ctypes.c_short

    class Win32InputBackend(InputBackend):
        def _send(self, inp: _INPUT) -> None:
            _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

        def key(self, vk: int, up: bool) -> None:
            inp = _INPUT(type=_INPUT_KEYBOARD)
            inp.u.ki = _KEYBDINPUT(wVk=vk, wScan=0, dwFlags=_KEYEVENTF_KEYUP if up else 0)
            self._send(inp)

        def unicode(self, ch: str, up: bool) -> None:
            # Characters outside the BMP are sent as their UTF-16 surrogate pair.
            units = ch.encode("utf-16-le")
            for i in range(0, len(units), 2):
                inp = _INPUT(type=_INPUT_KEYBOARD)
                code = int.from_bytes(units[i : i + 2], "little")
                flags = _KEYEVENTF_UNICODE | (_KEYEVENTF_KEYUP if up else 0)
                inp.u.ki = _KEYBDINPUT(wVk=0, wScan=code, dwFlags=flags)
                self._send(inp)

        def char_vk(self, ch: str) -> int | None:
            if len(ch) != 1:
                return None
            result = _user32.VkKeyScanW(ch)
            if result == -1:
                return None
            return result & 0xFF

        def mouse(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
            inp = _INPUT(type=_INPUT_MOUSE)
            inp.u.mi = _MOUSEINPUT(dx=dx, dy=dy, mouseData=ctypes.c_uint32(data).value, dwFlags=flags)
            self._send(inp)

        def virtual_screen(self) -> tuple[int, int, int, int]:
            gsm = _user32.GetSystemMetrics
            return gsm(76), gsm(77), max(1, gsm(78)), max(1, gsm(79))

    def default_backend() -> InputBackend:
        return Win32InputBackend()

else:  # pragma: no cover - non-Windows development hosts

    def default_backend() -> InputBackend:
        return InputBackend()


class InputController:
    """High-level input actions with the legacy host's semantics."""

    def __init__(self, backend: InputBackend | None = None) -> None:
        self.backend = backend or default_backend()

    # keyboard -----------------------------------------------------------------
    def type_text(self, text: str) -> None:
        for ch in text:
            self.backend.unicode(ch, up=False)
            self.backend.unicode(ch, up=True)

    def press_key(self, key: str) -> None:
        vk = VIRTUAL_KEYS.get(key.lower())
        if vk is not None:
            self.backend.key(vk, up=False)
        elif len(key) == 1:
            self.backend.unicode(key, up=False)

    def release_key(self, key: str) -> None:
        vk = VIRTUAL_KEYS.get(key.lower())
        if vk is not None:
            self.backend.key(vk, up=True)
        elif len(key) == 1:
            self.backend.unicode(key, up=True)

    def hotkey(self, keys: list[str]) -> None:
        # Single characters are mapped to virtual keys so combinations like ctrl+c work,
        # and every pressed key is released in reverse order (the legacy host leaked them).
        pressed: list[int] = []
        for key in keys:
            vk = VIRTUAL_KEYS.get(key.lower())
            if vk is None and len(key) == 1:
                vk = self.backend.char_vk(key)
            if vk is None:
                continue
            self.backend.key(vk, up=False)
            pressed.append(vk)
        for vk in reversed(pressed):
            self.backend.key(vk, up=True)

    # mouse --------------------------------------------------------------------
    def move_absolute(self, x: int, y: int) -> None:
        left, top, width, height = self.backend.virtual_screen()
        nx = round((x - left) * 65535.0 / max(1, width - 1))
        ny = round((y - top) * 65535.0 / max(1, height - 1))
        self.backend.mouse(_MOUSEEVENTF_MOVE | _MOUSEEVENTF_ABSOLUTE | _MOUSEEVENTF_VIRTUALDESK, nx, ny)

    def move_relative(self, dx: int, dy: int) -> None:
        self.backend.mouse(_MOUSEEVENTF_MOVE, dx, dy)

    def mouse_down(self, button: str) -> None:
        down, _, data = mouse_flags(button)
        self.backend.mouse(down, data=data)

    def mouse_up(self, button: str) -> None:
        _, up, data = mouse_flags(button)
        self.backend.mouse(up, data=data)

    def click(self, button: str, count: int = 1) -> None:
        for _ in range(max(1, count)):
            self.mouse_down(button)
            self.mouse_up(button)

    def scroll(self, dx: int, dy: int, precise: bool = False) -> None:
        """dx/dy are notches, or raw wheel units (120 = one notch) when precise (smooth scrolling)."""
        unit = 1 if precise else WHEEL_DELTA
        if dy:
            self.backend.mouse(_MOUSEEVENTF_WHEEL, data=max(-12000, min(12000, dy * unit)))
        if dx:
            self.backend.mouse(_MOUSEEVENTF_HWHEEL, data=max(-12000, min(12000, dx * unit)))

    # dispatch -----------------------------------------------------------------
    def handle_keyboard(self, msg: dict[str, Any]) -> None:
        match get_str(msg, "action").lower():
            case "type":
                self.type_text(get_str(msg, "text"))
            case "press":
                self.press_key(get_str(msg, "key"))
            case "release":
                self.release_key(get_str(msg, "key"))
            case "hotkey":
                self.hotkey(get_str_list(msg, "keys"))

    def handle_mouse(self, msg: dict[str, Any]) -> None:
        action = get_str(msg, "input_action", get_str(msg, "action")).lower()
        match action:
            case "move":
                self.move_absolute(get_int(msg, "x"), get_int(msg, "y"))
            case "move_relative":
                self.move_relative(get_int(msg, "dx"), get_int(msg, "dy"))
            case "click":
                self.click(get_str(msg, "button"), max(1, get_int(msg, "count", 1)))
            case "press":
                self.mouse_down(get_str(msg, "button"))
            case "release":
                self.mouse_up(get_str(msg, "button"))
            case "scroll":
                self.scroll(get_int(msg, "dx"), get_int(msg, "dy"), bool(msg.get("precise")))

    def run_macro_action(self, action: str) -> None:
        lowered = action.lower()
        if lowered.startswith("keyboard:"):
            key = action[len("keyboard:") :]
            if key.strip():
                self.press_key(key)
                self.release_key(key)
        elif lowered.startswith("mouse:"):
            self.click(action[len("mouse:") :], 1)


class InputFeature(Feature):
    message_types = ("keyboard", "mouse", "macro")

    def __init__(self, ctx, controller: InputController | None = None) -> None:
        super().__init__(ctx)
        self.controller = controller or InputController()

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        if msg_type == "keyboard":
            self.controller.handle_keyboard(msg)
        elif msg_type == "mouse":
            self.controller.handle_mouse(msg)
        elif msg_type == "macro":
            steps = msg.get("steps")
            if isinstance(steps, list):
                # Replay in the background so a long macro never blocks the receive loop; the
                # per-session lock keeps macros sequential, as the legacy host's inline replay was.
                lock = session.state.setdefault("macro_lock", asyncio.Lock())
                seq = session.state["macro_seq"] = session.state.get("macro_seq", 0) + 1
                session.run_task(f"macro:{seq}", self._replay(lock, steps))

    async def _replay(self, lock: asyncio.Lock, steps: list[Any]) -> None:
        async with lock:
            for step in steps:
                if not isinstance(step, dict):
                    continue
                action = get_str(step, "action")
                if action.strip():
                    self.controller.run_macro_action(action)
                delay = get_int(step, "delay")
                if delay > 0:
                    await asyncio.sleep(delay / 1000)
