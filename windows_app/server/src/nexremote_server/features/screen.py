"""PC screen streaming (SCRN JPEG frames), PC audio (AUDF) and pointer input on the shared screen."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from nexremote_server.features.audio import AudioCapture, audio_availability
from nexremote_server.features.base import Feature
from nexremote_server.protocol.constants import SCREEN_AUDIO_FRAME, SCREEN_FRAME
from nexremote_server.protocol.frames import build_frame
from nexremote_server.protocol.jsonutil import get_bool, get_int, get_int_list, get_str

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Monitor:
    index: int
    name: str
    left: int
    top: int
    width: int
    height: int
    is_primary: bool


def list_monitors() -> list[Monitor]:
    """Monitors in EnumDisplayMonitors order, named by device (\\\\.\\DISPLAY1), like the legacy host."""
    try:
        import win32api

        result = []
        for index, (hmon, _hdc, _rect) in enumerate(win32api.EnumDisplayMonitors()):
            info = win32api.GetMonitorInfo(hmon)
            left, top, right, bottom = info["Monitor"]
            result.append(
                Monitor(
                    index=index,
                    name=info.get("Device") or f"Display {index + 1}",
                    left=left,
                    top=top,
                    width=right - left,
                    height=bottom - top,
                    is_primary=bool(info.get("Flags", 0) & 1),
                )
            )
        if result:
            return result
    except Exception:
        log.debug("monitor enumeration failed", exc_info=True)
    return [Monitor(0, "Primary Display", 0, 0, 1920, 1080, True)]


def _fit_within(w: int, h: int, max_w: int, max_h: int) -> tuple[int, int]:
    scale = min(max_w / w, max_h / h, 1.0)
    return max(1, round(w * scale)), max(1, round(h * scale))


def target_size(w: int, h: int, resolution: str) -> tuple[int, int]:
    """Output size for a resolution preset; never upscales."""
    res = (resolution or "native").strip().lower()
    if res == "native":
        return w, h
    if res == "half":
        return max(1, w // 2), max(1, h // 2)
    if res == "720p":
        return _fit_within(w, h, 1280, 720)
    if res == "1080p":
        return _fit_within(w, h, 1920, 1080)
    match = re.fullmatch(r"(\d+)x(\d+)", res)
    if match:
        return _fit_within(w, h, int(match.group(1)), int(match.group(2)))
    return w, h


class ScreenGrabber:
    """Thread-safe grabber: one mss instance per worker thread."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _mss(self):
        inst = getattr(self._local, "mss", None)
        if inst is None:
            import mss

            inst = self._local.mss = mss.mss()
        return inst

    def capture_jpeg(self, monitor: Monitor, resolution: str, quality: int) -> bytes:
        import cv2
        import simplejpeg

        shot = self._mss().grab(
            {"left": monitor.left, "top": monitor.top, "width": monitor.width, "height": monitor.height}
        )
        frame = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)[:, :, :3]
        tw, th = target_size(shot.width, shot.height, resolution)
        if (tw, th) != (shot.width, shot.height):
            frame = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
        return simplejpeg.encode_jpeg(
            np.ascontiguousarray(frame),
            quality=max(1, min(100, quality)),
            colorspace="BGR",
            colorsubsampling="420",
        )


@dataclass
class ScreenState:
    fps: int = 30
    quality: int = 70
    resolution: str = "native"
    preferred_monitor: int = 0
    audio_enabled: bool = False
    audio: AudioCapture | None = None
    audio_format: dict[str, Any] | None = None


def resolve_coordinate(msg: dict[str, Any], norm_key: str, px_key: str, offset: int, size: int) -> int:
    value = msg.get(norm_key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        clamped = max(0.0, min(1.0, float(value)))
        return offset + round(clamped * max(0, size - 1))
    return offset + max(0, min(get_int(msg, px_key), max(0, size - 1)))


class ScreenShareFeature(Feature):
    message_types = ("screen_share",)

    def __init__(self, ctx, input_controller) -> None:
        super().__init__(ctx)
        self.input = input_controller
        self.grabber = ScreenGrabber()

    def _state(self, session) -> ScreenState:
        return session.state.setdefault("screen", ScreenState())

    def audio_status(self) -> tuple[bool, str]:
        """Cached; probing PortAudio is too slow for every feature_status build."""
        return getattr(self, "_audio_status", (False, "audio availability not checked yet"))

    async def start(self) -> None:
        self._audio_status = await asyncio.to_thread(audio_availability)
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def stop(self) -> None:
        task = getattr(self, "_refresh_task", None)
        if task is not None:
            task.cancel()

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            self._audio_status = await asyncio.to_thread(audio_availability)

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        st = self._state(session)
        action = get_str(msg, "action").lower()
        match action:
            case "start":
                st.fps = max(1, get_int(msg, "fps", st.fps))
                st.quality = max(1, min(100, get_int(msg, "quality", st.quality)))
                st.resolution = get_str(msg, "resolution", st.resolution)
                st.audio_enabled = get_bool(msg, "audio_enabled", st.audio_enabled)
                indices = get_int_list(msg, "display_indices") or [get_int(msg, "display_index", 0)]
                for index in indices:
                    self._start_stream(session, index)
                if st.audio_enabled:
                    await self._start_audio(session)
                else:
                    await self._stop_audio(session, send_update=False)
            case "stop":
                raw = msg.get("display_index")
                stop_index = raw if isinstance(raw, int) and not isinstance(raw, bool) else None
                self._stop_streams(session, stop_index)
                if stop_index is None or not session.task_names("screen:"):
                    await self._stop_audio(session, send_update=True)
            case "set_quality":
                st.quality = max(1, min(100, get_int(msg, "quality", st.quality)))
            case "set_resolution":
                st.resolution = get_str(msg, "resolution", st.resolution)
            case "set_fps":
                st.fps = max(1, get_int(msg, "fps", st.fps))
            case "set_monitor":
                st.preferred_monitor = get_int(msg, "monitor_index", st.preferred_monitor)
            case "set_audio_enabled":
                st.audio_enabled = get_bool(msg, "audio_enabled", st.audio_enabled)
                if st.audio_enabled and session.task_names("screen:"):
                    await self._start_audio(session)
                else:
                    await self._stop_audio(session, send_update=True)
            case "list_displays":
                await session.send_encrypted(self._display_list(session))
            case "input":
                await asyncio.to_thread(self._input, msg)

    def _display_list(self, session) -> dict[str, Any]:
        st = self._state(session)
        active = sorted(int(name.split(":", 1)[1]) for name in session.task_names("screen:"))
        return {
            "type": "screen_share",
            "action": "display_list",
            "displays": [
                {
                    "index": m.index,
                    "name": m.name,
                    "width": m.width,
                    "height": m.height,
                    "left": m.left,
                    "top": m.top,
                    "is_primary": m.is_primary,
                }
                for m in list_monitors()
            ],
            "active_displays": active,
            "current_resolution": st.resolution,
            "current_fps": st.fps,
            "current_quality": st.quality,
            "audio_enabled": st.audio_enabled,
            "audio_format": st.audio_format,
        }

    # video --------------------------------------------------------------------
    def _start_stream(self, session, index: int) -> None:
        monitors = list_monitors()
        monitor = next((m for m in monitors if m.index == index), monitors[0])
        session.run_task(f"screen:{index}", self._stream(session, index, monitor))

    def _stop_streams(self, session, index: int | None) -> None:
        for name in session.task_names("screen:"):
            if index is None or name == f"screen:{index}":
                session.cancel_task(name)

    async def _stream(self, session, index: int, monitor: Monitor) -> None:
        st = self._state(session)
        next_due = time.perf_counter()
        while session.is_open:
            try:
                jpeg = await asyncio.to_thread(self.grabber.capture_jpeg, monitor, st.resolution, st.quality)
            except Exception:
                log.debug("screen capture failed", exc_info=True)
                jpeg = b""
            if jpeg:
                await session.send_binary(build_frame(SCREEN_FRAME, index, jpeg))
            # Pace to the requested fps, counting capture time (the legacy host slept a full
            # interval after each capture, so it always ran slower than requested).
            interval = 1.0 / max(1, st.fps)
            next_due = max(next_due + interval, time.perf_counter())
            await asyncio.sleep(max(0.0, next_due - time.perf_counter()))

    # audio --------------------------------------------------------------------
    async def _start_audio(self, session) -> None:
        await self._stop_audio(session, send_update=False)
        st = self._state(session)
        loop = asyncio.get_running_loop()

        def on_chunk(chunk: bytes) -> None:
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(session.send_binary(build_frame(SCREEN_AUDIO_FRAME, 0, chunk)))
            )

        def on_error(code: str, message: str) -> None:
            def report() -> None:
                st.audio_enabled = False
                st.audio_format = None
                asyncio.ensure_future(
                    session.send_encrypted(
                        {"type": "screen_share", "action": "audio_error", "code": code, "message": message}
                    )
                )

            loop.call_soon_threadsafe(report)

        capture = AudioCapture(on_chunk, on_error)
        ok, fmt, code, message = await asyncio.to_thread(capture.start)
        if not ok or fmt is None:
            st.audio_enabled = False
            st.audio_format = None
            await session.send_encrypted(
                {
                    "type": "screen_share",
                    "action": "audio_error",
                    "code": code or "audio_start_failed",
                    "message": message or "System audio capture could not start.",
                }
            )
            return
        st.audio = capture
        st.audio_enabled = True
        st.audio_format = fmt
        await session.send_encrypted({"type": "screen_share", "action": "audio_format", **fmt})

    async def _stop_audio(self, session, send_update: bool) -> None:
        st = self._state(session)
        st.audio_enabled = False
        st.audio_format = None
        if st.audio is not None:
            capture, st.audio = st.audio, None
            await asyncio.to_thread(capture.stop)
        if send_update and session.is_open:
            await session.send_encrypted({"type": "screen_share", "action": "audio_stopped"})

    # input --------------------------------------------------------------------
    def _input(self, msg: dict[str, Any]) -> None:
        monitors = list_monitors()
        index = get_int(msg, "monitor_index", 0)
        m = next((mon for mon in monitors if mon.index == index), monitors[0] if monitors else None)
        if m is None:
            return
        x = resolve_coordinate(msg, "normalized_x", "x", m.left, m.width)
        y = resolve_coordinate(msg, "normalized_y", "y", m.top, m.height)
        action = get_str(msg, "input_action", get_str(msg, "action")).lower()
        button = get_str(msg, "button", "left")
        match action:
            case "move":
                self.input.move_absolute(x, y)
            case "press":
                self.input.move_absolute(x, y)
                self.input.mouse_down(button)
            case "release":
                self.input.move_absolute(x, y)
                self.input.mouse_up(button)
            case "click":
                self.input.move_absolute(x, y)
                self.input.click(button, max(1, get_int(msg, "count", 1)))
            case "scroll":
                self.input.move_absolute(x, y)
                self.input.scroll(
                    get_int(msg, "wheel_dx", get_int(msg, "dx")), get_int(msg, "wheel_dy", get_int(msg, "dy"))
                )

    async def on_session_closed(self, session) -> None:
        await self._stop_audio(session, send_update=False)
