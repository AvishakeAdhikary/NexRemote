"""PC webcam streaming (CAMF JPEG frames), gated by local consent on the PC."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from nexremote_server.features.base import Feature
from nexremote_server.protocol.constants import CAMERA_FRAME
from nexremote_server.protocol.frames import build_frame
from nexremote_server.protocol.jsonutil import get_int, get_int_list, get_str

log = logging.getLogger(__name__)

FRAME_INTERVAL_SECONDS = 0.1
FIRST_FRAME_TIMEOUT_SECONDS = 6.0
STALE_FRAME_SECONDS = 5.0
JPEG_QUALITY = 75


@dataclass(frozen=True, slots=True)
class CameraDescriptor:
    index: int
    name: str
    id: str


class CameraError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


async def enumerate_cameras() -> list[CameraDescriptor]:
    try:
        from winrt.windows.devices.enumeration import DeviceClass, DeviceInformation

        found = await DeviceInformation.find_all_async_device_class(DeviceClass.VIDEO_CAPTURE)
        return [CameraDescriptor(i, d.name, d.id) for i, d in enumerate(found)]
    except Exception:
        log.debug("camera enumeration failed", exc_info=True)
        return []


@dataclass
class _CameraWorker:
    descriptor: CameraDescriptor
    latest: bytes = b""
    latest_at: float = 0.0
    error: CameraError | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    first_frame: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    users: int = 0

    def run(self) -> None:
        import cv2
        import simplejpeg

        # DirectShow first: OpenCV's MSMF backend fails to open some integrated webcams.
        cap = cv2.VideoCapture(self.descriptor.index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(self.descriptor.index, cv2.CAP_MSMF)
        try:
            if not cap.isOpened():
                self.error = CameraError(
                    "access_denied",
                    "Windows denied access to the selected webcam. Check privacy settings and close any app that is exclusively using the camera.",
                )
                self.first_frame.set()
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            failures = 0
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    failures += 1
                    if failures > 50:
                        self.error = CameraError(
                            "device_lost", f"{self.descriptor.name} disconnected or stopped responding."
                        )
                        self.first_frame.set()
                        return
                    time.sleep(0.05)
                    continue
                failures = 0
                try:
                    self.latest = simplejpeg.encode_jpeg(frame, quality=JPEG_QUALITY, colorspace="BGR")
                    self.latest_at = time.monotonic()
                except Exception as exc:
                    self.error = CameraError("frame_encode_failed", f"Could not encode a camera frame: {exc}")
                self.first_frame.set()
        except Exception as exc:
            self.error = CameraError(
                "initialize_failed", f"NexRemote could not initialize {self.descriptor.name}: {exc}"
            )
            self.first_frame.set()
        finally:
            cap.release()


class CameraManager:
    """Host-wide camera workers shared by every session (one capture per physical camera)."""

    def __init__(self) -> None:
        self._workers: dict[int, _CameraWorker] = {}
        self._lock = threading.Lock()
        self._cache: list[CameraDescriptor] = []

    async def cameras(self) -> list[CameraDescriptor]:
        self._cache = await enumerate_cameras()
        return self._cache

    def is_active(self, index: int) -> bool:
        worker = self._workers.get(index)
        return worker is not None and worker.thread is not None and worker.thread.is_alive()

    def info(self, index: int, name: str | None = None) -> dict[str, Any]:
        descriptor = next((c for c in self._cache if c.index == index), None)
        return {
            "index": index,
            "name": name or (descriptor.name if descriptor else f"Camera {index + 1}"),
            "available": descriptor is not None,
            "active": descriptor is not None and self.is_active(index),
        }

    async def acquire(self, index: int) -> CameraDescriptor:
        cameras = await self.cameras()
        descriptor = next((c for c in cameras if c.index == index), None)
        if descriptor is None:
            raise CameraError("device_missing", "The selected camera is no longer available on the PC host.")
        with self._lock:
            worker = self._workers.get(index)
            if worker is None or worker.thread is None or not worker.thread.is_alive():
                worker = _CameraWorker(descriptor)
                worker.thread = threading.Thread(target=worker.run, name=f"camera-{index}", daemon=True)
                self._workers[index] = worker
                worker.thread.start()
            worker.users += 1
        started = await asyncio.to_thread(worker.first_frame.wait, FIRST_FRAME_TIMEOUT_SECONDS)
        if worker.error is not None or not started or not worker.latest:
            error = worker.error or CameraError(
                "frame_timeout",
                f"{descriptor.name} did not deliver a video frame in time. Check whether another app is locking the webcam.",
            )
            self.release(index, force=True)
            raise error
        return descriptor

    def release(self, index: int, force: bool = False) -> None:
        with self._lock:
            worker = self._workers.get(index)
            if worker is None:
                return
            worker.users = 0 if force else max(0, worker.users - 1)
            if worker.users == 0:
                worker.stop_event.set()
                del self._workers[index]

    def frame(self, index: int) -> tuple[bytes, CameraError | None]:
        worker = self._workers.get(index)
        if worker is None:
            return b"", CameraError("device_lost", f"Camera {index + 1} is not running.")
        if worker.error is not None:
            return b"", worker.error
        if time.monotonic() - worker.latest_at > STALE_FRAME_SECONDS:
            return b"", None
        return worker.latest, None

    def stop_all(self) -> None:
        with self._lock:
            for worker in self._workers.values():
                worker.stop_event.set()
            self._workers.clear()


class CameraFeature(Feature):
    message_types = ("camera",)

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.manager = CameraManager()

    def _active(self, session) -> set[int]:
        return session.state.setdefault("cameras", set())

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        if not self.ctx.settings.current.camera_access_consent_granted:
            await session.send_encrypted(
                {"type": "camera", "action": "permission_required", "permission": "camera"}
            )
            return
        action = get_str(msg, "action").lower()
        match action:
            case "list_cameras":
                cameras = await self.manager.cameras()
                await session.send_encrypted(
                    {
                        "type": "camera",
                        "action": "camera_list",
                        "cameras": [
                            {
                                "index": c.index,
                                "name": c.name,
                                "id": c.id,
                                "available": True,
                                "active": self.manager.is_active(c.index),
                            }
                            for c in cameras
                        ],  # fmt: skip
                    }
                )
            case "start":
                index = get_int(msg, "camera_index", 0)
                descriptor = await self._start(session, index)
                if descriptor is not None:
                    await session.send_encrypted(
                        {
                            "type": "camera",
                            "action": "started",
                            "camera_index": index,
                            "camera_info": self.manager.info(index, descriptor.name),
                        }  # fmt: skip
                    )
            case "start_multi":
                started = [i for i in get_int_list(msg, "camera_indices") if await self._start(session, i)]
                if started:
                    await session.send_encrypted(
                        {"type": "camera", "action": "multi_started", "camera_indices": started}
                    )
            case "stop":
                index = get_int(msg, "camera_index", 0)
                self._stop(session, index)
                await session.send_encrypted({"type": "camera", "action": "stopped", "camera_index": index})
            case "stop_all":
                self._stop_all(session)
                await session.send_encrypted({"type": "camera", "action": "stopped_all"})
            case "set_camera":
                index = get_int(msg, "camera_index", 0)
                self._stop_all(session)
                descriptor = await self._start(session, index)
                if descriptor is not None:
                    await session.send_encrypted(
                        {
                            "type": "camera",
                            "action": "camera_changed",
                            "camera_index": index,
                            "camera_info": self.manager.info(index, descriptor.name),
                        }  # fmt: skip
                    )

    async def _send_error(self, session, index: int, error: CameraError) -> None:
        await session.send_encrypted(
            {
                "type": "camera",
                "action": "error",
                "camera_index": index,
                "code": error.code,
                "message": error.message,
            }
        )

    async def _start(self, session, index: int) -> CameraDescriptor | None:
        if index in self._active(session):
            self._stop(session, index)
        try:
            descriptor = await self.manager.acquire(index)
        except CameraError as error:
            await self._send_error(session, index, error)
            return None
        self._active(session).add(index)
        session.run_task(f"camera:{index}", self._stream(session, index))
        return descriptor

    def _stop(self, session, index: int) -> None:
        session.cancel_task(f"camera:{index}")
        if index in self._active(session):
            self._active(session).discard(index)
            self.manager.release(index)

    def _stop_all(self, session) -> None:
        for index in list(self._active(session)):
            self._stop(session, index)

    async def _stream(self, session, index: int) -> None:
        while session.is_open:
            frame, error = self.manager.frame(index)
            if not frame:
                self._active(session).discard(index)
                self.manager.release(index)
                await self._send_error(
                    session,
                    index,
                    error
                    or CameraError(
                        "frame_timeout",
                        f"Camera {index + 1} stopped because the PC host no longer receives live frames from the webcam.",
                    ),
                )
                return
            await session.send_binary(build_frame(CAMERA_FRAME, index, frame))
            await asyncio.sleep(FRAME_INTERVAL_SECONDS)

    async def on_session_closed(self, session) -> None:
        self._stop_all(session)

    async def stop(self) -> None:
        self.manager.stop_all()
