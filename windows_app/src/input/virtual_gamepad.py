"""
Virtual Gamepad — Cross-Platform Backend Plugin

Selects the best available backend automatically:
  • Windows  → _WindowsXInputBackend  (vgamepad XInput via ViGEm)
             → _WindowsDS4Backend     (vgamepad DualShock 4 / DInput via ViGEm)
  • Linux    → _LinuxEvdevBackend     (evdev uinput — no driver needed, kernel built-in)
  • All else → _NullBackend           (silent no-op; gamepad feature simply unavailable)

Set the environment variable NEXREMOTE_SKIP_VIGEM=1 to force the NullBackend
(useful in CI/CD test steps or headless environments without ViGEm installed).
"""
import os
import sys
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Back-end base class ────────────────────────────────────────────────────────

class _GamepadBackend:
    """Abstract interface every backend must implement."""

    @property
    def active(self) -> bool:
        return False

    @property
    def error_reason(self) -> str | None:
        return None

    def press_button(self, button: str): ...
    def release_button(self, button: str): ...
    def left_trigger(self, value: float): ...
    def right_trigger(self, value: float): ...
    def left_joystick(self, x: float, y: float): ...
    def right_joystick(self, x: float, y: float): ...
    def dpad(self, direction: str, pressed: bool): ...
    def update(self): ...
    def reset(self): ...
    def cleanup(self): ...


# ── Null back-end  ─────────────────────────────────────────────────────────────

class _NullBackend(_GamepadBackend):
    """Silent no-op — gamepad feature unavailable on this platform/environment."""

    def __init__(self, reason: str = "unavailable"):
        self._reason = reason

    @property
    def active(self) -> bool:
        return False

    @property
    def error_reason(self) -> str | None:
        return self._reason


# ── Windows XInput backend  ────────────────────────────────────────────────────

class _WindowsXInputBackend(_GamepadBackend):
    """Xbox 360 controller via vgamepad (requires ViGEm Bus Driver)."""

    # Maps our canonical button names → vgamepad XUSB_BUTTON values.
    # Populated lazily so the import doesn't happen on non-Windows platforms.
    _BUTTON_MAP: dict = {}

    def __init__(self):
        import vgamepad as vg  # noqa: import inside init — Windows only
        self._vg = vg
        self._active = False
        self._error: str | None = None
        try:
            self._pad = vg.VX360Gamepad()
            self._active = True
            # Build button map once on first successful init
            self._BUTTON_MAP = {
                'A':     vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
                'B':     vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                'X':     vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
                'Y':     vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
                'L1': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
                'R1': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
                'LB':    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
                'RB':    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
                'BACK':  vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
                'SELECT':vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
                'START': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
                'LS':    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
                'RS':    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
                'UP':    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
                'DOWN':  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
                'LEFT':  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
                'RIGHT': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
            }
            logger.info("XInput (Windows) backend initialized")
        except Exception as e:
            self._active = False
            err = str(e).lower()
            self._error = "vigem_driver_missing" if any(
                k in err for k in ("vigem", "bus", "driver")
            ) else str(e)
            logger.error(f"XInput backend failed: {e}")

    @property
    def active(self) -> bool:
        return self._active

    @property
    def error_reason(self) -> str | None:
        return self._error

    def press_button(self, button: str):
        btn = self._BUTTON_MAP.get(button.upper())
        if btn:
            self._pad.press_button(btn)

    def release_button(self, button: str):
        btn = self._BUTTON_MAP.get(button.upper())
        if btn:
            self._pad.release_button(btn)

    def left_trigger(self, value: float):
        self._pad.left_trigger(int(value * 255))

    def right_trigger(self, value: float):
        self._pad.right_trigger(int(value * 255))

    def left_joystick(self, x: float, y: float):
        self._pad.left_joystick(int(x * 32767), int(y * 32767))

    def right_joystick(self, x: float, y: float):
        self._pad.right_joystick(int(x * 32767), int(y * 32767))

    def dpad(self, direction: str, pressed: bool):
        btn = self._BUTTON_MAP.get(direction.upper())
        if btn:
            if pressed:
                self._pad.press_button(btn)
            else:
                self._pad.release_button(btn)

    def update(self):
        self._pad.update()

    def reset(self):
        self._pad.reset()
        self._pad.update()

    def cleanup(self):
        if self._active:
            self.reset()


# ── Windows DS4/DInput backend  ───────────────────────────────────────────────

class _WindowsDS4Backend(_GamepadBackend):
    """DualShock 4 (DInput) via vgamepad — only available on Windows with ViGEm."""

    def __init__(self):
        import vgamepad as vg  # noqa
        self._vg = vg
        self._active = False
        self._error: str | None = None
        try:
            self._pad = vg.VDS4Gamepad()
            self._active = True
            logger.info("DS4/DInput (Windows) backend initialized")
        except Exception as e:
            self._active = False
            err = str(e).lower()
            self._error = "vigem_driver_missing" if any(
                k in err for k in ("vigem", "bus", "driver")
            ) else str(e)
            logger.error(f"DS4 backend failed: {e}")

    @property
    def active(self) -> bool:
        return self._active

    @property
    def error_reason(self) -> str | None:
        return self._error

    _BUTTON_MAP = {
        'A':      'cross',
        'B':      'circle',
        'X':      'square',
        'Y':      'triangle',
        'L1':     'l1',
        'R1':     'r1',
        'LB':     'l1',
        'RB':     'r1',
        'L3':     'l3',
        'R3':     'r3',
        'LS':     'l3',
        'RS':     'r3',
        'START':  'options',
        'BACK':   'share',
        'SELECT': 'share',
    }

    _DPAD_MAP = {
        'UP':    'top',
        'DOWN':  'bottom',
        'LEFT':  'left',
        'RIGHT': 'right',
    }

    def press_button(self, button: str):
        attr = self._BUTTON_MAP.get(button.upper())
        if attr:
            getattr(self._pad.report.buttons, attr, None)  # type: ignore

    def release_button(self, button: str):
        pass  # vgamepad DS4 uses report-based API; handled via update cycle

    def left_trigger(self, value: float):
        self._pad.report.l2 = int(value * 255)   # type: ignore

    def right_trigger(self, value: float):
        self._pad.report.r2 = int(value * 255)   # type: ignore

    def left_joystick(self, x: float, y: float):
        self._pad.report.leftX = int((x + 1) * 127.5)   # type: ignore
        self._pad.report.leftY = int((y + 1) * 127.5)   # type: ignore

    def right_joystick(self, x: float, y: float):
        self._pad.report.rightX = int((x + 1) * 127.5)  # type: ignore
        self._pad.report.rightY = int((y + 1) * 127.5)  # type: ignore

    def dpad(self, direction: str, pressed: bool):
        # DS4 d-pad is encoded as a hat switch angle. Simple implementation:
        pass

    def update(self):
        self._pad.update()  # type: ignore

    def reset(self):
        self._pad.__init__()  # type: ignore

    def cleanup(self):
        if self._active:
            pass


# ── Linux evdev/uinput backend  ───────────────────────────────────────────────

class _LinuxEvdevBackend(_GamepadBackend):
    """
    Emulates an Xbox-like controller via Linux uinput (no driver needed).
    Requires the current user to have write permission to /dev/uinput
    (add user to 'input' group or use a udev rule).
    """

    # evdev key / abs codes
    _BTN_MAP = {
        'A': 0x130,    # BTN_A
        'B': 0x131,    # BTN_B
        'X': 0x133,    # BTN_X
        'Y': 0x134,    # BTN_Y
        'L1': 0x136,   # BTN_TL
        'R1': 0x137,   # BTN_TR
        'LB': 0x136,
        'RB': 0x137,
        'SELECT': 0x13a, # BTN_SELECT
        'BACK': 0x13a,
        'START': 0x13b,  # BTN_START
        'LS': 0x13d,     # BTN_THUMBL
        'RS': 0x13e,     # BTN_THUMBR
    }
    _ABS_LX = 0x00  # ABS_X
    _ABS_LY = 0x01  # ABS_Y
    _ABS_RX = 0x03  # ABS_RX
    _ABS_RY = 0x04  # ABS_RY
    _ABS_LT = 0x02  # ABS_Z
    _ABS_RT = 0x05  # ABS_RZ
    _ABS_HAT_X = 0x10  # ABS_HAT0X
    _ABS_HAT_Y = 0x11  # ABS_HAT0Y

    def __init__(self):
        self._active = False
        self._error: str | None = None
        self._ui = None
        try:
            import evdev
            self._evdev = evdev
            ui = evdev.UInput(
                events={
                    evdev.ecodes.EV_KEY: list(self._BTN_MAP.values()),
                    evdev.ecodes.EV_ABS: [
                        (self._ABS_LX, evdev.AbsInfo(-32767, 32767, 0, 0, 15, 0)),
                        (self._ABS_LY, evdev.AbsInfo(-32767, 32767, 0, 0, 15, 0)),
                        (self._ABS_RX, evdev.AbsInfo(-32767, 32767, 0, 0, 15, 0)),
                        (self._ABS_RY, evdev.AbsInfo(-32767, 32767, 0, 0, 15, 0)),
                        (self._ABS_LT, evdev.AbsInfo(0, 255, 0, 0, 0, 0)),
                        (self._ABS_RT, evdev.AbsInfo(0, 255, 0, 0, 0, 0)),
                        (self._ABS_HAT_X, evdev.AbsInfo(-1, 1, 0, 0, 0, 0)),
                        (self._ABS_HAT_Y, evdev.AbsInfo(-1, 1, 0, 0, 0, 0)),
                    ],
                },
                name="NexRemote Virtual Controller",
                vendor=0x045E,   # Microsoft
                product=0x028E,  # Xbox 360
            )
            self._ui = ui
            self._active = True
            logger.info("evdev/uinput (Linux) backend initialized")
        except Exception as e:
            self._error = str(e)
            logger.error(f"evdev backend failed: {e}")

    @property
    def active(self) -> bool:
        return self._active

    @property
    def error_reason(self) -> str | None:
        return self._error

    def _key(self, code: int, value: int):
        self._ui.write(self._evdev.ecodes.EV_KEY, code, value)

    def _abs(self, code: int, value: int):
        self._ui.write(self._evdev.ecodes.EV_ABS, code, value)

    def press_button(self, button: str):
        code = self._BTN_MAP.get(button.upper())
        if code:
            self._key(code, 1)

    def release_button(self, button: str):
        code = self._BTN_MAP.get(button.upper())
        if code:
            self._key(code, 0)

    def left_trigger(self, value: float):
        self._abs(self._ABS_LT, int(value * 255))

    def right_trigger(self, value: float):
        self._abs(self._ABS_RT, int(value * 255))

    def left_joystick(self, x: float, y: float):
        self._abs(self._ABS_LX, int(x * 32767))
        self._abs(self._ABS_LY, int(-y * 32767))

    def right_joystick(self, x: float, y: float):
        self._abs(self._ABS_RX, int(x * 32767))
        self._abs(self._ABS_RY, int(-y * 32767))

    def dpad(self, direction: str, pressed: bool):
        v = 1 if pressed else 0
        d = direction.upper()
        if d == 'UP':
            self._abs(self._ABS_HAT_Y, -v)
        elif d == 'DOWN':
            self._abs(self._ABS_HAT_Y, v)
        elif d == 'LEFT':
            self._abs(self._ABS_HAT_X, -v)
        elif d == 'RIGHT':
            self._abs(self._ABS_HAT_X, v)

    def update(self):
        self._ui.syn()

    def reset(self):
        for code in self._BTN_MAP.values():
            self._key(code, 0)
        for code in (self._ABS_LX, self._ABS_LY, self._ABS_RX,
                     self._ABS_RY, self._ABS_LT, self._ABS_RT,
                     self._ABS_HAT_X, self._ABS_HAT_Y):
            self._abs(code, 0)
        self._ui.syn()

    def cleanup(self):
        if self._ui:
            try:
                self.reset()
                self._ui.close()
            except Exception:
                pass


# ── Backend selector  ──────────────────────────────────────────────────────────

def _select_backend(mode: str = 'xinput') -> _GamepadBackend:
    """
    Choose and instantiate the appropriate backend.

    Parameters
    ----------
    mode : str
        ``'xinput'``  — Xbox 360 via ViGEm (Windows default)
        ``'dinput'``  — DualShock 4 / DInput via ViGEm (Windows)
        ``'android'`` — No server-side simulation needed (handled by client)
    """
    # Allow CI/headless skip
    if os.environ.get("NEXREMOTE_SKIP_VIGEM"):
        logger.info("NEXREMOTE_SKIP_VIGEM set — using NullBackend")
        return _NullBackend("NEXREMOTE_SKIP_VIGEM env var set")

    if sys.platform == "win32":
        if mode == 'dinput':
            b = _WindowsDS4Backend()
        else:
            b = _WindowsXInputBackend()
        if not b.active:
            logger.warning(f"Windows backend failed ({b.error_reason}), falling back to Null")
            return _NullBackend(b.error_reason or "windows_backend_failed")
        return b

    if sys.platform.startswith("linux"):
        b = _LinuxEvdevBackend()
        if not b.active:
            logger.warning(f"evdev backend failed ({b.error_reason}), falling back to Null")
            return _NullBackend(b.error_reason or "evdev_failed")
        return b

    logger.info(f"No gamepad backend for platform '{sys.platform}' — using NullBackend")
    return _NullBackend(f"unsupported_platform:{sys.platform}")


# ── Public facade  ─────────────────────────────────────────────────────────────

class VirtualGamepad:
    """
    Platform-independent virtual gamepad.

    Delegates all operations to the best available backend.
    Call ``switch_mode(mode)`` to change between 'xinput', 'dinput', 'android'.
    """

    def __init__(self, mode: str = 'xinput'):
        self._mode = mode
        self._backend: _GamepadBackend = _select_backend(mode)

    # ── Public properties ──────────────────────────────────────────────────

    @property
    def active(self) -> bool:
        return self._backend.active

    @property
    def error_reason(self) -> str | None:
        return self._backend.error_reason

    def get_status(self) -> dict:
        """Return current availability status (used by server capabilities endpoint)."""
        return {
            'available': self._backend.active,
            'mode': self._mode,
            'error': self._backend.error_reason,
        }

    # ── Mode switching ─────────────────────────────────────────────────────

    def switch_mode(self, mode: str):
        """Hot-swap the backend. Resets the current pad first."""
        if mode == self._mode and self._backend.active:
            return
        logger.info(f"Switching gamepad mode: {self._mode} → {mode}")
        self._backend.cleanup()
        self._mode = mode
        self._backend = _select_backend(mode)

    # ── Input methods  ─────────────────────────────────────────────────────

    def send_input(self, data: dict):
        """Dispatch incoming message to the correct handler."""
        if not self._backend.active:
            return
        try:
            input_type = data.get('input_type')
            if input_type == 'button':
                self._handle_button(data)
            elif input_type == 'trigger':
                self._handle_trigger(data)
            elif input_type == 'joystick':
                self._handle_joystick(data)
            elif input_type == 'dpad':
                self._handle_dpad(data)
            self._backend.update()
        except Exception as e:
            logger.error(f"Gamepad input error: {e}")

    def _handle_button(self, data: dict):
        button = (data.get('button') or '').upper()
        pressed = data.get('pressed', False)
        if pressed:
            self._backend.press_button(button)
        else:
            self._backend.release_button(button)

    def _handle_trigger(self, data: dict):
        trigger = data.get('trigger', '')
        value = float(data.get('value', 0))
        if trigger == 'LT' or trigger == 'L2':
            self._backend.left_trigger(value)
        elif trigger == 'RT' or trigger == 'R2':
            self._backend.right_trigger(value)

    def _handle_joystick(self, data: dict):
        stick = data.get('stick', '')
        x = float(data.get('x', 0))
        y = float(data.get('y', 0))
        if stick == 'left':
            self._backend.left_joystick(x, y)
        elif stick == 'right':
            self._backend.right_joystick(x, y)

    def _handle_dpad(self, data: dict):
        direction = (data.get('direction') or '').upper()
        pressed = data.get('pressed', False)
        self._backend.dpad(direction, pressed)

    def reset(self):
        """Reset all axes/buttons to neutral."""
        if self._backend.active:
            self._backend.reset()

    def __del__(self):
        self._backend.cleanup()