"""
Screen Capture
High-performance screen capture with dedicated capture thread.
Maintains a persistent mss instance in a single thread, providing
a shared frame buffer that can be read from the asyncio event loop
without blocking.
"""
import mss
import cv2
import numpy as np
import base64
import time
from threading import Thread, Lock, Event
from utils.logger import get_logger

logger = get_logger(__name__)


# Resolution presets: (max_width, max_height) or None for native
RESOLUTION_PRESETS = {
    'native': None,
    '1080p': (1920, 1080),
    '720p': (1280, 720),
    '480p': (854, 480),
}


class ScreenCapture:
    """High-performance screen capture with dedicated thread"""

    def __init__(self, config):
        self.config = config

        # Settings (can be changed at runtime)
        self.fps = config.get('screen_fps', 30)
        self.quality = config.get('screen_quality', 70)  # JPEG 1-100
        self.resolution = 'native'  # key into RESOLUTION_PRESETS
        self.monitor_index = 1  # mss monitor index (1 = primary)

        # Shared frame buffer
        self._frame_bytes = None       # Latest JPEG bytes (not base64)
        self._frame_lock = Lock()
        self._native_width = 0
        self._native_height = 0
        self._encoded_width = 0
        self._encoded_height = 0

        # Capture thread
        self._running = Event()
        self._capture_thread = None

        # Monitor info (populated on first start)
        self._monitors_cache = []

        logger.info("Screen capture initialized")

    def start(self):
        """Start the capture thread"""
        if self._capture_thread and self._capture_thread.is_alive():
            return

        self._running.set()
        self._capture_thread = Thread(
            target=self._capture_loop,
            daemon=True,
            name="ScreenCaptureThread"
        )
        self._capture_thread.start()
        logger.info(f"Screen capture thread started ({self.fps} fps target)")

    def stop(self):
        """Stop the capture thread"""
        self._running.clear()
        if self._capture_thread:
            self._capture_thread.join(timeout=3)
            self._capture_thread = None
        logger.info("Screen capture thread stopped")

    def _capture_loop(self):
        """Main capture loop — runs in dedicated thread with persistent mss"""
        try:
            with mss.mss() as sct:
                # Cache monitor info
                self._monitors_cache = list(sct.monitors)

                while self._running.is_set():
                    start = time.perf_counter()

                    try:
                        # Select monitor
                        if self.monitor_index < len(sct.monitors):
                            monitor = sct.monitors[self.monitor_index]
                        else:
                            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]

                        # Capture screenshot
                        screenshot = sct.grab(monitor)
                        frame = np.array(screenshot)  # BGRA

                        self._native_width = frame.shape[1]
                        self._native_height = frame.shape[0]

                        # Convert BGRA → BGR
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                        # Resize if resolution preset is not native
                        preset = RESOLUTION_PRESETS.get(self.resolution)
                        if preset:
                            max_w, max_h = preset
                            h, w = frame.shape[:2]
                            if w > max_w or h > max_h:
                                scale = min(max_w / w, max_h / h)
                                new_w = int(w * scale)
                                new_h = int(h * scale)
                                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                        self._encoded_width = frame.shape[1]
                        self._encoded_height = frame.shape[0]

                        # Encode as JPEG
                        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                        ok, buffer = cv2.imencode('.jpg', frame, encode_params)

                        if ok:
                            jpeg_bytes = buffer.tobytes()
                            with self._frame_lock:
                                self._frame_bytes = jpeg_bytes

                    except Exception as e:
                        logger.error(f"Capture error: {e}")

                    # Maintain target FPS
                    elapsed = time.perf_counter() - start
                    sleep_time = (1.0 / self.fps) - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Capture thread crashed: {e}", exc_info=True)

    # --- Public read API (called from asyncio thread, non-blocking) ---

    def get_latest_frame(self) -> bytes | None:
        """Get the latest JPEG frame bytes (non-blocking)"""
        with self._frame_lock:
            return self._frame_bytes

    def get_latest_frame_base64(self) -> str:
        """Get the latest frame as base64 string"""
        frame = self.get_latest_frame()
        if frame:
            return base64.b64encode(frame).decode('utf-8')
        return ""

    def get_frame_info(self) -> dict:
        """Get info about current capture"""
        return {
            'native_width': self._native_width,
            'native_height': self._native_height,
            'encoded_width': self._encoded_width,
            'encoded_height': self._encoded_height,
            'fps': self.fps,
            'quality': self.quality,
            'resolution': self.resolution,
            'monitor_index': self.monitor_index,
        }

    # --- Settings ---

    def set_monitor(self, monitor_index: int):
        """Set which monitor to capture (1-based index)"""
        self.monitor_index = monitor_index
        logger.info(f"Monitor set to {monitor_index}")

    def set_quality(self, quality: int):
        """Set JPEG quality (1-100)"""
        self.quality = max(1, min(100, quality))
        logger.info(f"Quality set to {self.quality}")

    def set_fps(self, fps: int):
        """Set target FPS (1-60)"""
        self.fps = max(1, min(60, fps))
        logger.info(f"FPS set to {self.fps}")

    def set_resolution(self, resolution: str):
        """Set resolution preset: 'native', '1080p', '720p', '480p'"""
        if resolution in RESOLUTION_PRESETS:
            self.resolution = resolution
            logger.info(f"Resolution set to {resolution}")
        else:
            logger.warning(f"Unknown resolution preset: {resolution}")

    # --- Monitor enumeration ---

    def get_monitors(self) -> list:
        """Get list of available monitors"""
        monitors = []
        try:
            # Use cached data if capture thread is running, else create temp instance
            mon_list = self._monitors_cache if self._monitors_cache else []
            if not mon_list:
                with mss.mss() as sct:
                    mon_list = list(sct.monitors)

            for i, monitor in enumerate(mon_list[1:], 1):  # Skip "all monitors"
                monitors.append({
                    'id': i,
                    'width': monitor['width'],
                    'height': monitor['height'],
                    'left': monitor['left'],
                    'top': monitor['top']
                })
        except Exception as e:
            logger.error(f"Error getting monitors: {e}")
        return monitors

    # Legacy compat
    def capture_frame(self) -> str:
        """Legacy: capture a single frame as base64"""
        return self.get_latest_frame_base64()

    def start_streaming(self, callback):
        """Legacy compat — not used in new architecture"""
        self.start()

    def stop_streaming(self):
        """Legacy compat"""
        self.stop()

    def __del__(self):
        self.stop()