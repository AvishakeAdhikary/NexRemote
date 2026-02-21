"""
Screen Capture — Multi-monitor with per-monitor dedicated threads.

Architecture
------------
* `MonitorCapture`  — one capture thread per physical monitor.  Each maintains
  a persistent mss instance and writes the latest JPEG frame to a shared slot.
* `MultiScreenCapture` — owns a dict of `MonitorCapture` instances; starts /
  stops them on demand.  Public API matches the original `ScreenCapture` so the
  rest of the codebase requires minimal changes, but extends it with:
    - get_monitors()              — enumerate physical displays
    - start_monitor(index)        — start capturing a specific monitor (1-based)
    - stop_monitor(index)         — stop a specific monitor
    - get_latest_frame(index)     — per-monitor frame read (non-blocking)
    - get_all_active_monitors()   — list of currently-streaming monitor indices
"""
import mss
import cv2
import numpy as np
import time
from threading import Thread, Lock, Event
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Resolution presets ─────────────────────────────────────────────────────────
RESOLUTION_PRESETS: dict[str, tuple[int, int] | None] = {
    'native': None,
    '1080p': (1920, 1080),
    '720p': (1280, 720),
    '480p': (854, 480),
    '360p': (640, 360),
}

QUALITY_PRESETS: dict[str, int] = {
    'low': 30,
    'medium': 50,
    'high': 70,
    'ultra': 90,
}


class MonitorCapture:
    """
    Dedicated capture thread for ONE physical monitor.

    •  Runs a persistent mss instance — creating mss once and keeping it alive
       is significantly faster than creating a new one per frame.
    •  Adaptive sleep: targets the requested FPS; if encoding is slower than
       the target interval the loop yields immediately rather than over-sleeping.
    •  Thread-safe frame slot: a single Lock protects a bytes field.
       Readers (asyncio push loop) never block the capture thread.
    """

    def __init__(self, monitor_index: int, fps: int = 30, quality: int = 70,
                 resolution: str = 'native'):
        self.monitor_index = monitor_index   # mss index (1 = primary)
        self.fps = fps
        self.quality = quality
        self.resolution = resolution

        self._frame: bytes | None = None
        self._lock = Lock()
        self._running = Event()

        self._thread: Thread | None = None

        # Info updated from the capture thread
        self.native_width = 0
        self.native_height = 0
        self.encoded_width = 0
        self.encoded_height = 0

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = Thread(
            target=self._loop,
            daemon=True,
            name=f"CaptureThread-mon{self.monitor_index}",
        )
        self._thread.start()
        logger.info(f"Monitor {self.monitor_index} capture started "
                    f"({self.fps} fps, q{self.quality}, {self.resolution})")

    def stop(self):
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        with self._lock:
            self._frame = None
        logger.info(f"Monitor {self.monitor_index} capture stopped")

    @property
    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Frame access (non-blocking, called from asyncio push loop) ─────────────

    def get_latest_frame(self) -> bytes | None:
        with self._lock:
            return self._frame

    # ── Settings (thread-safe — values read by the capture thread each frame) ─

    def set_fps(self, fps: int):
        self.fps = max(1, min(60, fps))

    def set_quality(self, quality: int):
        self.quality = max(1, min(100, quality))

    def set_resolution(self, resolution: str):
        if resolution in RESOLUTION_PRESETS:
            self.resolution = resolution

    # ── Capture loop ──────────────────────────────────────────────────────────

    def _loop(self):
        try:
            with mss.mss() as sct:
                while self._running.is_set():
                    t0 = time.perf_counter()
                    try:
                        self._capture_one(sct)
                    except Exception as e:
                        logger.error(f"Capture error (mon {self.monitor_index}): {e}")

                    elapsed = time.perf_counter() - t0
                    target = 1.0 / max(1, self.fps)
                    wait = target - elapsed
                    if wait > 0:
                        time.sleep(wait)
        except Exception as e:
            logger.error(
                f"Capture thread crashed (mon {self.monitor_index}): {e}",
                exc_info=True,
            )

    def _capture_one(self, sct: mss.mss):
        monitors = sct.monitors
        if self.monitor_index >= len(monitors):
            mon = monitors[1] if len(monitors) > 1 else monitors[0]
        else:
            mon = monitors[self.monitor_index]

        shot = sct.grab(mon)
        frame = np.array(shot)                          # BGRA
        self.native_width = frame.shape[1]
        self.native_height = frame.shape[0]

        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # BGR

        preset = RESOLUTION_PRESETS.get(self.resolution)
        if preset:
            max_w, max_h = preset
            h, w = frame.shape[:2]
            if w > max_w or h > max_h:
                scale = min(max_w / w, max_h / h)
                frame = cv2.resize(
                    frame,
                    (int(w * scale), int(h * scale)),
                    interpolation=cv2.INTER_AREA,
                )

        self.encoded_width = frame.shape[1]
        self.encoded_height = frame.shape[0]

        ok, buf = cv2.imencode(
            '.jpg', frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.quality],
        )
        if ok:
            with self._lock:
                self._frame = buf.tobytes()


class MultiScreenCapture:
    """
    Manages multiple `MonitorCapture` instances — one per active monitor.

    Backwards-compatible with the original `ScreenCapture` API used by
    `server.py`.  Extensions for multi-monitor support:
        start_monitor(index)     — start a specific monitor (1-based mss index)
        stop_monitor(index)      — stop a specific monitor
        get_latest_frame(index)  — get frame for a specific monitor
        get_all_active_monitors()— list of active monitor indices
    """

    def __init__(self, config: dict):
        self.config = config

        # Defaults (legacy single-monitor API path)
        self.fps:        int = config.get('screen_fps', 30)
        self.quality:    int = config.get('screen_quality', 70)
        self.resolution: str = 'native'
        self.monitor_index: int = 1   # 1-based mss index

        # Per-monitor capture instances  {mss_index: MonitorCapture}
        self._captures: dict[int, MonitorCapture] = {}
        self._captures_lock = Lock()

        # Monitor info (lazily populated)
        self._monitors_info: list[dict] = []

        logger.info("MultiScreenCapture initialized")

    # ── Legacy single-monitor API (used by server.py) ──────────────────────────

    def start(self):
        """Start capture for the currently selected monitor."""
        self.start_monitor(self.monitor_index)

    def stop(self):
        """Stop ALL active monitors."""
        with self._captures_lock:
            for cap in list(self._captures.values()):
                cap.stop()
            self._captures.clear()
        logger.info("All screen captures stopped")

    def get_latest_frame(self, monitor_index: int | None = None) -> bytes | None:
        """Return the latest JPEG frame for the given monitor (or current default)."""
        idx = monitor_index if monitor_index is not None else self.monitor_index
        with self._captures_lock:
            cap = self._captures.get(idx)
        return cap.get_latest_frame() if cap else None

    def get_frame_info(self, monitor_index: int | None = None) -> dict:
        idx = monitor_index if monitor_index is not None else self.monitor_index
        with self._captures_lock:
            cap = self._captures.get(idx)
        if cap:
            return {
                'native_width':  cap.native_width,
                'native_height': cap.native_height,
                'encoded_width': cap.encoded_width,
                'encoded_height': cap.encoded_height,
                'fps':           cap.fps,
                'quality':       cap.quality,
                'resolution':    cap.resolution,
                'monitor_index': idx,
            }
        return {
            'native_width': 0, 'native_height': 0,
            'encoded_width': 0, 'encoded_height': 0,
            'fps': self.fps, 'quality': self.quality,
            'resolution': self.resolution, 'monitor_index': idx,
        }

    # ── Multi-monitor API ──────────────────────────────────────────────────────

    def start_monitor(self, index: int):
        """Start capturing for monitor `index` (1-based mss index).  Idempotent."""
        with self._captures_lock:
            if index in self._captures and self._captures[index].is_alive:
                # Update settings on existing capture
                cap = self._captures[index]
                cap.set_fps(self.fps)
                cap.set_quality(self.quality)
                cap.set_resolution(self.resolution)
                return
            cap = MonitorCapture(
                monitor_index=index,
                fps=self.fps,
                quality=self.quality,
                resolution=self.resolution,
            )
            self._captures[index] = cap
        cap.start()

    def stop_monitor(self, index: int):
        """Stop capturing for monitor `index`."""
        with self._captures_lock:
            cap = self._captures.pop(index, None)
        if cap:
            cap.stop()

    def get_all_active_monitors(self) -> list[int]:
        """Return list of monitor indices currently being captured."""
        with self._captures_lock:
            return [idx for idx, cap in self._captures.items() if cap.is_alive]

    def is_monitor_active(self, index: int) -> bool:
        with self._captures_lock:
            cap = self._captures.get(index)
            return cap is not None and cap.is_alive

    # ── Settings (apply to all running + future captures) ─────────────────────

    def set_monitor(self, monitor_index: int):
        self.monitor_index = monitor_index
        logger.info(f"Default monitor set to {monitor_index}")

    def set_quality(self, quality: int):
        self.quality = max(1, min(100, quality))
        with self._captures_lock:
            for cap in self._captures.values():
                cap.set_quality(self.quality)
        logger.info(f"Quality set to {self.quality}")

    def set_fps(self, fps: int):
        self.fps = max(1, min(60, fps))
        with self._captures_lock:
            for cap in self._captures.values():
                cap.set_fps(self.fps)
        logger.info(f"FPS set to {self.fps}")

    def set_resolution(self, resolution: str):
        if resolution in RESOLUTION_PRESETS:
            self.resolution = resolution
            with self._captures_lock:
                for cap in self._captures.values():
                    cap.set_resolution(resolution)
            logger.info(f"Resolution set to {resolution}")

    # ── Monitor enumeration ────────────────────────────────────────────────────

    def get_monitors(self) -> list[dict]:
        """
        Enumerate physical displays.  Returns list of:
            {id, width, height, left, top, label}
        id is 1-based (mss convention).
        """
        try:
            with mss.mss() as sct:
                raw = list(sct.monitors)
                self._monitors_info = raw
        except Exception as e:
            logger.error(f"Monitor enumeration failed: {e}")
            raw = self._monitors_info or []

        monitors = []
        for i, mon in enumerate(raw[1:], 1):   # skip index-0 (virtual all-screens)
            w, h = mon['width'], mon['height']
            monitors.append({
                'id':     i,
                'width':  w,
                'height': h,
                'left':   mon['left'],
                'top':    mon['top'],
                'label':  f"Display {i}  ({w}×{h})",
                'is_primary': (mon['left'] == 0 and mon['top'] == 0),
            })
        return monitors

    # ── Legacy compat ──────────────────────────────────────────────────────────

    def capture_frame(self) -> str:
        import base64
        frame = self.get_latest_frame()
        return base64.b64encode(frame).decode() if frame else ''

    def start_streaming(self, callback):
        self.start()

    def stop_streaming(self):
        self.stop()

    def get_latest_frame_base64(self) -> str:
        import base64
        frame = self.get_latest_frame()
        return base64.b64encode(frame).decode() if frame else ''

    def __del__(self):
        self.stop()


# Alias so existing `from streaming.screen_capture import ScreenCapture` still works
ScreenCapture = MultiScreenCapture