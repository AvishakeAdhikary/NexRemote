"""Phone → PC screen sharing (PSCR H.264 frames) and PC → phone remote control.

The phone advertises a share with `{"type":"phone_screen","action":"start",...}` and then
streams PSCR binary frames. The host relays them to the desktop UI over the control API's
/events socket, prefixed with the device id so several phones can share at once:

    [1 byte n][n bytes device_id UTF-8][PSCR frame as received]

Since 1.2 the phone can also stream its playback audio (PAUD frames: 8-byte big-endian pts in
µs + PCM16 LE interleaved). The PC asks for it per phone with `audio_request {enabled}`; the phone
answers with `audio_changed {audio_active, sample_rate, channels}`. PAUD frames are relayed to the
UI with the same device-id prefix as video; the UI tells them apart by the 4-byte tag.

Input from the UI is forwarded to the phone as encrypted `phone_screen`/`input` messages, but
only while the phone said control is available and the PC user has phone control enabled.
The phone enforces its own consent too; the host check is defence in depth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from nexremote_server.features.base import Feature, available
from nexremote_server.protocol.constants import PHONE_AUDIO_FRAME, PHONE_SCREEN_FRAME
from nexremote_server.protocol.frames import parse_phone_screen
from nexremote_server.protocol.jsonutil import get_bool, get_float, get_int, get_str

log = logging.getLogger(__name__)

INPUT_ACTIONS = {"tap", "long_press", "swipe", "key"}
KEYS = {"back", "home", "recents"}


@dataclass
class PhoneScreenState:
    active: bool = False
    codec: str = "h264"
    width: int = 0
    height: int = 0
    fps: int = 30
    rotation: int = 0
    control_available: bool = False
    audio_available: bool = False
    audio_active: bool = False
    sample_rate: int = 48000
    channels: int = 2
    config: bytes = b""  # last codec-config frame, replayed to UI viewers that join late
    frames: int = 0

    def describe(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "codec": self.codec,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "rotation": self.rotation,
            "control_available": self.control_available,
            "audio_available": self.audio_available,
            "audio_active": self.audio_active,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
        }


def relay_prefix(device_id: str) -> bytes:
    raw = device_id.encode("utf-8")[:255]
    return bytes([len(raw)]) + raw


def sanitize_input(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Validate a UI input event and build the wire message for the phone."""
    action = get_str(msg, "input_action").lower()
    if action not in INPUT_ACTIONS:
        return None
    out: dict[str, Any] = {"type": "phone_screen", "action": "input", "input_action": action}
    if action == "key":
        key = get_str(msg, "key").lower()
        if key not in KEYS:
            return None
        out["key"] = key
        return out

    def norm(name: str) -> float:
        return max(0.0, min(1.0, get_float(msg, name)))

    out["normalized_x"] = norm("normalized_x")
    out["normalized_y"] = norm("normalized_y")
    if action == "swipe":
        out["end_x"] = norm("end_x")
        out["end_y"] = norm("end_y")
    duration = get_int(msg, "duration_ms", {"tap": 50, "long_press": 600, "swipe": 250}[action])
    out["duration_ms"] = max(1, min(5000, duration))
    return out


class PhoneScreenFeature(Feature):
    message_types = ("phone_screen",)

    def _state(self, session) -> PhoneScreenState:
        return session.state.setdefault("phone_screen", PhoneScreenState())

    def status(self) -> dict[str, Any]:
        if self.ctx.settings.current.phone_control_enabled:
            return available("Phone screen sharing and remote control are ready.")
        return available("Phone screen sharing is ready. Remote control is turned off on this PC.")

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        st = self._state(session)
        match get_str(msg, "action").lower():
            case "start" | "config_changed" as action:
                st.active = True
                st.codec = get_str(msg, "codec", st.codec) or "h264"
                st.width = get_int(msg, "width", st.width)
                st.height = get_int(msg, "height", st.height)
                st.fps = get_int(msg, "fps", st.fps)
                st.rotation = get_int(msg, "rotation", st.rotation)
                st.control_available = get_bool(msg, "control_available", st.control_available)
                st.audio_available = get_bool(msg, "audio_available", st.audio_available)
                if action == "start":
                    st.config = b""
                    st.frames = 0
                    st.audio_active = False
                self.ctx.bus.publish(
                    "phone_screen_started" if action == "start" else "phone_screen_changed",
                    {"device_id": session.device_id, "device_name": session.device_name, **st.describe()},
                )
            case "stop":
                self._stopped(session)
            case "audio_changed":
                st.audio_active = get_bool(msg, "audio_active", False)
                st.sample_rate = max(8000, min(96000, get_int(msg, "sample_rate", st.sample_rate)))
                st.channels = max(1, min(2, get_int(msg, "channels", st.channels)))
                if "audio_available" in msg:
                    st.audio_available = get_bool(msg, "audio_available", st.audio_available)
                self.ctx.bus.publish(
                    "phone_screen_changed",
                    {"device_id": session.device_id, "device_name": session.device_name, **st.describe()},
                )
            case "control_changed":
                st.control_available = get_bool(msg, "control_available", st.control_available)
                self.ctx.bus.publish(
                    "phone_screen_changed",
                    {"device_id": session.device_id, "device_name": session.device_name, **st.describe()},
                )

    async def handle_binary(self, session, tag: bytes, data: bytes) -> bool:
        if tag == PHONE_AUDIO_FRAME:
            st = self._state(session)
            if st.active and st.audio_active and self.ctx.bus.has_subscribers:
                self.ctx.bus.publish_binary(relay_prefix(session.device_id) + data)
            return True
        if tag != PHONE_SCREEN_FRAME:
            return False
        st = self._state(session)
        packet = parse_phone_screen(data)
        if packet is None or not st.active:
            return True
        if packet.is_config:
            st.config = data
        st.frames += 1
        if self.ctx.bus.has_subscribers:
            self.ctx.bus.publish_binary(relay_prefix(session.device_id) + data)
        return True

    def _stopped(self, session) -> None:
        st = self._state(session)
        if st.active:
            st.active = False
            self.ctx.bus.publish("phone_screen_stopped", {"device_id": session.device_id})

    async def on_session_closed(self, session) -> None:
        self._stopped(session)

    # called from the control API ---------------------------------------------
    def active_shares(self) -> list[dict[str, Any]]:
        shares = []
        for session in self.ctx.sessions.values():
            st = session.state.get("phone_screen")
            if isinstance(st, PhoneScreenState) and st.active:
                shares.append(
                    {"device_id": session.device_id, "device_name": session.device_name, **st.describe()}
                )
        return shares

    def cached_config_frames(self) -> list[bytes]:
        frames = []
        for session in self.ctx.sessions.values():
            st = session.state.get("phone_screen")
            if isinstance(st, PhoneScreenState) and st.active and st.config:
                frames.append(relay_prefix(session.device_id) + st.config)
        return frames

    async def send_input(self, device_id: str, msg: dict[str, Any]) -> str | None:
        """Forward one input event. Returns an error string, or None on success."""
        session = self.ctx.find_session(device_id)
        if session is None:
            return "device_not_connected"
        st = self._state(session)
        if not st.active:
            return "not_sharing"
        if not self.ctx.settings.current.phone_control_enabled:
            return "control_disabled_on_pc"
        if not st.control_available:
            return "control_not_allowed_on_phone"
        wire = sanitize_input(msg)
        if wire is None:
            return "invalid_input"
        await session.send_encrypted(wire)
        return None

    async def request_keyframe(self, device_id: str) -> str | None:
        session = self.ctx.find_session(device_id)
        if session is None:
            return "device_not_connected"
        if not self._state(session).active:
            return "not_sharing"
        await session.send_encrypted({"type": "phone_screen", "action": "request_keyframe"})
        return None

    async def request_audio(self, device_id: str, enabled: bool) -> str | None:
        """Ask the phone to start or stop streaming its playback audio to this PC."""
        session = self.ctx.find_session(device_id)
        if session is None:
            return "device_not_connected"
        st = self._state(session)
        if not st.active:
            return "not_sharing"
        if enabled and not st.audio_available:
            return "audio_not_available_on_phone"
        await session.send_encrypted({"type": "phone_screen", "action": "audio_request", "enabled": bool(enabled)})
        return None

    async def stop_share(self, device_id: str) -> str | None:
        session = self.ctx.find_session(device_id)
        if session is None:
            return "device_not_connected"
        await session.send_encrypted({"type": "phone_screen", "action": "stop_request"})
        return None
