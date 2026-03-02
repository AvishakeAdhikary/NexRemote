"""
Connection Approval Dialog
Shows when a new device wants to connect.

Thread safety: The approval future belongs to the asyncio event loop.
We must use loop.call_soon_threadsafe() to set its result from the Qt thread.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QGroupBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionApprovalDialog(QDialog):
    """Dialog for approving/rejecting connection requests"""

    def __init__(self, device_id: str, device_name: str,
                 future: asyncio.Future, loop: asyncio.AbstractEventLoop,
                 parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.device_name = device_name
        self._future = future
        self._loop = loop

        self.setWindowTitle("New Connection Request")
        self.setModal(True)
        self.setMinimumWidth(400)

        self._timeout_remaining = 60
        self._setup_ui()

        # Countdown timer
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("New Device Connection Request")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Device info group
        info_group = QGroupBox("Device Information")
        info_layout = QVBoxLayout()

        name_label = QLabel(f"Device Name: {self.device_name}")
        name_font = QFont()
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        info_layout.addWidget(name_label)

        id_label = QLabel(f"Device ID: {self.device_id[:16]}...")
        id_label.setStyleSheet("color: gray;")
        info_layout.addWidget(id_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Warning
        warning = QLabel("⚠️ Only approve if you recognize this device")
        warning.setStyleSheet("color: orange; font-weight: bold;")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)

        # Buttons
        button_layout = QHBoxLayout()

        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        reject_btn.clicked.connect(self._on_reject)
        button_layout.addWidget(reject_btn)

        approve_btn = QPushButton("Approve")
        approve_btn.setStyleSheet("""
            QPushButton {
                background-color: #388e3c;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2e7d32;
            }
        """)
        approve_btn.clicked.connect(self._on_approve)
        button_layout.addWidget(approve_btn)

        layout.addLayout(button_layout)

        # Timeout label
        self._timeout_label = QLabel(f"Auto-reject in {self._timeout_remaining} seconds")
        self._timeout_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timeout_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self._timeout_label)

    # ── Thread-safe Future resolution ──────────────────────────────────────

    def _resolve(self, value: bool):
        """Set the Future result from the asyncio event loop thread."""
        if self._future.done():
            return
        try:
            self._loop.call_soon_threadsafe(self._future.set_result, value)
        except RuntimeError:
            # Loop already closed
            logger.warning("Event loop closed before approval could be resolved")

    # ── Button handlers ────────────────────────────────────────────────────

    def _on_approve(self):
        logger.info(f"User approved connection from {self.device_name}")
        self._resolve(True)
        self._timer.stop()
        self.accept()

    def _on_reject(self):
        logger.info(f"User rejected connection from {self.device_name}")
        self._resolve(False)
        self._timer.stop()
        super().reject()  # QDialog.reject() — NOT self.reject()

    # ── Countdown ──────────────────────────────────────────────────────────

    def _tick(self):
        self._timeout_remaining -= 1
        self._timeout_label.setText(f"Auto-reject in {self._timeout_remaining} seconds")
        if self._timeout_remaining <= 0:
            logger.info(f"Approval timeout for {self.device_name}")
            self._resolve(False)
            self._timer.stop()
            super().reject()

    # ── Close = reject ─────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._resolve(False)
        self._timer.stop()
        super().closeEvent(event)