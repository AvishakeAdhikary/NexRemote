"""
Camera Streamer (Server-side)
Captures from PC cameras using OpenCV and streams JPEG frames to mobile clients.
"""
import os
# Suppress Microsoft Media Foundation hardware transform warnings (must be before cv2 import)
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
# Suppress DSHOW verbose error/warning output at the OS level
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"

import cv2
import time
from threading import Thread, Lock, Event
from utils.logger import get_logger

logger = get_logger(__name__)


class CameraStreamer:
    """Captures from PC cameras and provides frames for streaming to clients."""

    def __init__(self, config):
        self.config = config

        # Camera state
        self._capture: cv2.VideoCapture | None = None
        self._camera_index = 0
        self._running = Event()
        self._capture_thread: Thread | None = None

        # Shared frame buffer (latest JPEG bytes)
        self._frame_bytes: bytes | None = None
        self._frame_lock = Lock()

        # Camera native properties (populated on open)
        self._native_fps = 30.0
        self._native_width = 0
        self._native_height = 0
        self._quality = 70  # JPEG encode quality (1–100)

        logger.info("Camera streamer initialized")

    # ─── Camera Enumeration ────────────────────────────────────────────────────

    def list_cameras(self) -> list:
        """
        Enumerate available video capture devices (indices 0–9).
        Probes each index using a DirectShow backend (Windows) with
        output redirected to devnull to suppress DSHOW console noise.
        """
        cameras = []

        for i in range(10):
            # Use CAP_DSHOW for fastest open/close on Windows
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                # Stop probing once we hit a gap of 2 consecutive missing indices
                # (indices above the highest real device will all fail)
                if i > 0 and len(cameras) == 0 and i >= 2:
                    break
                continue

            try:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0 or fps > 1000:
                    fps = 30.0

                # Try to get a meaningful backend name for the label
                try:
                    backend = cap.getBackendName()
                except AttributeError:
                    backend = ""

                name = f"Camera {i}" + (f" ({backend})" if backend else "")

                cameras.append({
                    'index': i,
                    'name': name,
                    'width': w,
                    'height': h,
                    'fps': round(fps, 1),
                })
                logger.info(f"Found camera {i}: {w}×{h} @ {fps:.1f} fps")
            except Exception as e:
                logger.debug(f"Error reading camera {i} properties: {e}")
            finally:
                cap.release()

        logger.info(f"Camera enumeration complete: {len(cameras)} device(s) found")
        return cameras

    # ─── Start / Stop ─────────────────────────────────────────────────────────

    def start(self, camera_index: int = 0):
        """Start capturing from the given camera index."""
        # Stop any existing capture cleanly before opening a new one
        self.stop()

        self._camera_index = camera_index
        self._running.set()
        self._capture_thread = Thread(
            target=self._capture_loop,
            daemon=True,
            name=f"CameraCapture-{camera_index}",
        )
        self._capture_thread.start()
        logger.info(f"Camera capture started (index={camera_index})")

    def stop(self):
        """Stop the capture loop and release the camera device."""
        if not self._running.is_set() and self._capture_thread is None:
            return  # Already stopped

        self._running.clear()

        if self._capture_thread is not None:
            self._capture_thread.join(timeout=3)
            self._capture_thread = None

        # Clear the frame buffer
        with self._frame_lock:
            self._frame_bytes = None

        logger.info("Camera capture stopped")

    # ─── Capture Loop ─────────────────────────────────────────────────────────

    def _capture_loop(self):
        """Main capture loop — runs in a dedicated daemon thread."""
        cap = None
        try:
            cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                logger.error(f"Failed to open camera {self._camera_index}")
                return

            # Read native properties
            self._native_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._native_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._native_fps = cap.get(cv2.CAP_PROP_FPS)
            if self._native_fps <= 0 or self._native_fps > 1000:
                self._native_fps = 30.0

            frame_interval = 1.0 / self._native_fps
            logger.info(
                f"Camera {self._camera_index} opened: "
                f"{self._native_width}×{self._native_height} @ {self._native_fps:.1f} fps"
            )

            while self._running.is_set():
                start = time.perf_counter()

                ret, frame = cap.read()
                if not ret:
                    # Camera might have been disconnected
                    logger.warning(f"Camera {self._camera_index} read failed — retrying")
                    time.sleep(0.05)
                    continue

                # Encode as JPEG and store in shared buffer
                ok, buffer = cv2.imencode(
                    '.jpg', frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), self._quality]
                )
                if ok:
                    with self._frame_lock:
                        self._frame_bytes = buffer.tobytes()

                # Pace to native camera FPS
                elapsed = time.perf_counter() - start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Camera capture thread crashed: {e}", exc_info=True)
        finally:
            if cap is not None:
                cap.release()
                logger.debug(f"Camera {self._camera_index} device released")

    # ─── Public Read API ──────────────────────────────────────────────────────

    def get_latest_frame(self) -> bytes | None:
        """Return the latest JPEG frame bytes (non-blocking, may be None)."""
        with self._frame_lock:
            return self._frame_bytes

    def get_camera_info(self) -> dict:
        """Return current camera properties."""
        return {
            'index': self._camera_index,
            'width': self._native_width,
            'height': self._native_height,
            'fps': round(self._native_fps, 1),
            'active': self._running.is_set(),
        }

    def set_quality(self, quality: int):
        """Set JPEG encode quality (1–100)."""
        self._quality = max(1, min(100, quality))

    @property
    def is_active(self) -> bool:
        return self._running.is_set()

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
