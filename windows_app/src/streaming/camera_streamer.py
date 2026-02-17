"""
Camera Streamer (Server-side)
Captures from PC cameras using OpenCV and streams frames to mobile clients.
Replaces the old VirtualCamera which received frames FROM the client.
"""
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import cv2
import time
import base64
from threading import Thread, Lock, Event
from utils.logger import get_logger

logger = get_logger(__name__)


class CameraStreamer:
    """Captures from PC cameras and provides frames for streaming to clients"""

    def __init__(self, config):
        self.config = config

        # Camera state
        self._capture = None
        self._camera_index = 0
        self._running = Event()
        self._capture_thread = None

        # Shared frame buffer
        self._frame_bytes = None
        self._frame_lock = Lock()

        # Camera properties
        self._native_fps = 30.0
        self._native_width = 0
        self._native_height = 0
        self._quality = 70  # JPEG quality

        logger.info("Camera streamer initialized")

    def list_cameras(self) -> list:
        """Enumerate available cameras on the system"""
        cameras = []
        for i in range(5):  # Check indices 0-4
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if fps <= 0:
                        fps = 30.0

                    # Try to get camera name via backend
                    name = f"Camera {i}"
                    backend = cap.getBackendName()
                    if backend:
                        name = f"Camera {i} ({backend})"

                    cameras.append({
                        'index': i,
                        'name': name,
                        'width': w,
                        'height': h,
                        'fps': round(fps, 1),
                    })
                    cap.release()
                else:
                    cap.release()
            except Exception:
                pass

        logger.info(f"Found {len(cameras)} camera(s)")
        return cameras

    def start(self, camera_index: int = 0):
        """Start capturing from the given camera"""
        self.stop()  # Stop any existing capture

        self._camera_index = camera_index
        self._running.set()
        self._capture_thread = Thread(
            target=self._capture_loop,
            daemon=True,
            name="CameraCaptureThread"
        )
        self._capture_thread.start()
        logger.info(f"Camera capture started (index={camera_index})")

    def stop(self):
        """Stop capturing"""
        self._running.clear()
        if self._capture_thread:
            self._capture_thread.join(timeout=3)
            self._capture_thread = None

        with self._frame_lock:
            self._frame_bytes = None

        logger.info("Camera capture stopped")

    def _capture_loop(self):
        """Main capture loop — runs in dedicated thread"""
        try:
            cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                logger.error(f"Failed to open camera {self._camera_index}")
                return

            # Read native properties
            self._native_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._native_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._native_fps = cap.get(cv2.CAP_PROP_FPS)
            if self._native_fps <= 0:
                self._native_fps = 30.0

            logger.info(f"Camera opened: {self._native_width}x{self._native_height} @ {self._native_fps} fps")

            while self._running.is_set():
                start = time.perf_counter()

                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                # Encode as JPEG
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self._quality]
                ok, buffer = cv2.imencode('.jpg', frame, encode_params)

                if ok:
                    jpeg_bytes = buffer.tobytes()
                    with self._frame_lock:
                        self._frame_bytes = jpeg_bytes

                # Pace to native FPS
                elapsed = time.perf_counter() - start
                sleep_time = (1.0 / self._native_fps) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            cap.release()

        except Exception as e:
            logger.error(f"Camera capture thread crashed: {e}", exc_info=True)

    # --- Public read API ---

    def get_latest_frame(self) -> bytes | None:
        """Get latest JPEG frame bytes (non-blocking)"""
        with self._frame_lock:
            return self._frame_bytes

    def get_camera_info(self) -> dict:
        """Get current camera properties"""
        return {
            'index': self._camera_index,
            'width': self._native_width,
            'height': self._native_height,
            'fps': round(self._native_fps, 1),
            'active': self._running.is_set(),
        }

    def set_quality(self, quality: int):
        """Set JPEG quality (1-100)"""
        self._quality = max(1, min(100, quality))

    @property
    def is_active(self) -> bool:
        return self._running.is_set()

    def __del__(self):
        self.stop()
