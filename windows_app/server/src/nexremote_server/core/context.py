"""Process-wide state shared by the protocol server, features and control API."""

from __future__ import annotations

import logging
from typing import Any

from nexremote_server.config import Config
from nexremote_server.core.approvals import ApprovalService
from nexremote_server.core.events import EventBus
from nexremote_server.core.session import ClientSession
from nexremote_server.db.engine import EventLog, SettingsStore, TrustedDeviceStore
from nexremote_server.features.adb import AdbBridgeFeature
from nexremote_server.features.base import Feature, available, unavailable
from nexremote_server.features.camera import CameraFeature
from nexremote_server.features.clipboard import ClipboardFeature
from nexremote_server.features.files import FileExplorerFeature
from nexremote_server.features.gamepad import GamepadFeature
from nexremote_server.features.input import InputController, InputFeature
from nexremote_server.features.media import MediaFeature
from nexremote_server.features.phone_screen import PhoneScreenFeature
from nexremote_server.features.screen import ScreenShareFeature
from nexremote_server.features.tasks import TaskManagerFeature
from nexremote_server.net.certs import CertificateInfo
from nexremote_server.protocol.constants import LEGAL_DOCUMENT_VERSION, PROTOCOL_VERSION

log = logging.getLogger(__name__)


class AppContext:
    def __init__(
        self,
        config: Config,
        settings: SettingsStore,
        trusted: TrustedDeviceStore,
        events: EventLog,
        cert: CertificateInfo,
        input_controller: InputController | None = None,
    ) -> None:
        self.config = config
        self.settings = settings
        self.trusted = trusted
        self.events = events
        self.cert = cert
        self.bus = EventBus()
        self.approvals = ApprovalService(self.bus)
        self.sessions: dict[str, ClientSession] = {}  # keyed by lower-cased device id
        self.running = False

        controller = input_controller or InputController()
        self.input = InputFeature(self, controller)
        self.gamepad = GamepadFeature(self, controller)
        self.screen = ScreenShareFeature(self, controller)
        self.media = MediaFeature(self, controller)
        self.camera = CameraFeature(self)
        self.files = FileExplorerFeature(self)
        self.tasks = TaskManagerFeature(self)
        self.clipboard = ClipboardFeature(self)
        self.adb = AdbBridgeFeature(self)
        self.phone_screen = PhoneScreenFeature(self)
        self.features: list[Feature] = [
            self.input, self.gamepad, self.screen, self.media, self.camera,
            self.files, self.tasks, self.clipboard, self.adb, self.phone_screen,
        ]  # fmt: skip
        self.routes: dict[str, Feature] = {t: f for f in self.features for t in f.message_types}

    # sessions -----------------------------------------------------------------
    def find_session(self, device_id: str) -> ClientSession | None:
        return self.sessions.get(device_id.lower())

    # capability reporting -----------------------------------------------------
    def capabilities(self) -> dict[str, Any]:
        gamepad_ready = self.gamepad.ready
        settings = self.settings.current
        return {
            "keyboard": True,
            "mouse": True,
            "gamepad": gamepad_ready,
            "gamepad_available": gamepad_ready,
            "gamepad_mode": self.gamepad.mode or "xinput",
            "gamepad_modes": ["xinput", "dinput", "android"],
            "screen_streaming": True,
            "screen_audio_streaming": self.screen.audio_status()[0],
            "camera_streaming": settings.camera_access_consent_granted,
            "file_transfer": True,
            "clipboard": True,
            "multi_display": True,
            # v1.1 additions; older clients ignore unknown keys
            "phone_screen": True,
            "phone_control": settings.phone_control_enabled,
            "protocol_versions": [1, 2],
        }

    def feature_status(self) -> dict[str, dict[str, Any]]:
        audio_ok, audio_reason = self.screen.audio_status()
        settings = self.settings.current
        return {
            "touchpad": available("Remote pointer and keyboard control are ready."),
            "media_control": available("Media control is ready."),
            "screen_share": available("Screen sharing is ready."),
            "screen_audio": available("Screen-share audio is ready.")
            if audio_ok
            else unavailable(
                f"System audio loopback capture is unavailable: {audio_reason}"
                if audio_reason
                else "System audio loopback capture is unavailable on this PC.",
                "restart_server",
            ),
            "file_explorer": available("File explorer is ready."),
            "task_manager": available("Task manager is ready."),
            "clipboard": available("Clipboard sync is ready."),
            "camera": available("Camera streaming is ready.")
            if settings.camera_access_consent_granted
            else unavailable("Camera streaming requires local consent on the PC.", "grant_camera_consent"),
            "gamepad": self.gamepad.status(),
            "usb_bridge": self.adb.status(),
            "phone_screen": self.phone_screen.status(),
        }

    def discovery_response(self) -> dict[str, Any]:
        s = self.settings.current
        return {
            "type": "discovery_response",
            "name": s.pc_name,
            "port": s.server_port,
            "port_insecure": s.server_port_insecure,
            "id": s.device_id,
            "version": PROTOCOL_VERSION,
            "cert_fingerprint": self.cert.fingerprint,
        }

    def qr_payload(self, host: str) -> dict[str, Any]:
        s = self.settings.current
        return {
            "host": host,
            "port": s.server_port,
            "port_insecure": s.server_port_insecure,
            "name": s.pc_name,
            "id": s.device_id,
            "cert_fingerprint": self.cert.fingerprint,
        }

    # gating -------------------------------------------------------------------
    def can_serve(self) -> tuple[bool, str]:
        s = self.settings.current
        if not s.legal_current(LEGAL_DOCUMENT_VERSION):
            return False, "legal_not_accepted"
        if not s.remote_control_consent_granted:
            return False, "consent_required"
        if not s.enable_remote_access:
            return False, "remote_access_disabled"
        return True, ""

    def publish_status(self) -> None:
        self.bus.publish("status_changed", {"feature_status": self.feature_status()})
