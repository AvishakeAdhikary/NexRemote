"""
Main Application Window.
Owns the server lifecycle — start/stop via a toggle button.
Shows a QR code for mobile app connection.
"""
import io
import json
import socket
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QGroupBox,
    QSystemTrayIcon, QMenu, QMessageBox, QListWidgetItem,
    QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QIcon, QAction, QPixmap, QImage, QDesktopServices
import os
import qrcode
from PIL import Image as PilImage

from ui.settings_dialog import SettingsDialog
from ui.connection_dialog import ConnectionApprovalDialog
from ui.tray_icon import TrayIcon
from utils.logger import get_logger
from utils.paths import get_assets_dir

logger = get_logger(__name__)


def _get_lan_ip() -> str:
    """Get the most likely LAN IP address of this machine."""
    try:
        # Connect to a public DNS to determine the outgoing interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class MainWindow(QMainWindow):
    """Main application window — owns server lifecycle."""

    # Emitted when the user requests a server toggle from the tray
    server_toggle_requested = pyqtSignal()

    def __init__(self, server, server_thread, config):
        super().__init__()
        self.server = server
        self.server_thread = server_thread
        self.config = config
        self._server_running = False

        self.setWindowTitle("NexRemote")
        self.setMinimumSize(650, 520)

        # Set window icon from local assets
        assets = get_assets_dir()
        logo_path = assets / 'images' / 'logo.png'
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # Connect server signals
        self.server.client_connected.connect(self.on_client_connected)
        self.server.client_disconnected.connect(self.on_client_disconnected)

        self.setup_ui()
        self.setup_tray_icon()

        # Connect internal signal
        self.server_toggle_requested.connect(self._toggle_server)

    # ─── UI Setup ────────────────────────────────────────────────────────

    def setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # ── Top row: status + QR code ──
        top_layout = QHBoxLayout()

        # Left: Server status group
        status_group = QGroupBox("Server")
        status_layout = QVBoxLayout()

        # Server toggle button
        self.server_btn = QPushButton("Start Server")
        self.server_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; "
            "font-weight: bold; padding: 10px; border-radius: 6px; font-size: 14px; }"
            "QPushButton:hover { background-color: #27ae60; }"
        )
        self.server_btn.clicked.connect(self._toggle_server)
        status_layout.addWidget(self.server_btn)

        # Status indicator
        self.status_label = QLabel("● Server Stopped")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px;")
        status_layout.addWidget(self.status_label)

        # PC info
        pc_name = self.config.get('pc_name', 'Unknown PC')
        self.pc_info_label = QLabel(f"PC Name: {pc_name}")
        status_layout.addWidget(self.pc_info_label)

        # Port info
        port = self.config.get('server_port', 8765)
        port_insecure = self.config.get('server_port_insecure', 8766)
        self.port_label = QLabel(f"Ports: {port} (secure) / {port_insecure} (fallback)")
        status_layout.addWidget(self.port_label)

        # IP info
        self.ip_label = QLabel(f"LAN IP: {_get_lan_ip()}")
        status_layout.addWidget(self.ip_label)

        status_group.setLayout(status_layout)
        top_layout.addWidget(status_group, stretch=2)

        # Right: QR code
        qr_group = QGroupBox("Quick Connect")
        qr_layout = QVBoxLayout()
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_label = QLabel("Start the server to\nshow QR code")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setStyleSheet(
            "border: 2px dashed #555; border-radius: 8px; color: #888; font-size: 13px;"
        )
        qr_layout.addWidget(self.qr_label)

        qr_hint = QLabel("Scan from the NexRemote mobile app")
        qr_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_hint.setStyleSheet("color: #888; font-size: 11px;")
        qr_layout.addWidget(qr_hint)

        qr_group.setLayout(qr_layout)
        top_layout.addWidget(qr_group, stretch=1)

        layout.addLayout(top_layout)

        # ── Connected clients section ──
        clients_group = QGroupBox("Connected Devices")
        clients_layout = QVBoxLayout()

        self.clients_list = QListWidget()
        clients_layout.addWidget(self.clients_list)

        clients_group.setLayout(clients_layout)
        layout.addWidget(clients_group)

        # ── Bottom buttons ──
        button_layout = QHBoxLayout()

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_btn)

        self.about_btn = QPushButton("ℹ About")
        self.about_btn.clicked.connect(self.show_about)
        button_layout.addWidget(self.about_btn)

        self.support_btn = QPushButton("☕ Support / Donate")
        self.support_btn.setStyleSheet(
            "QPushButton { background-color: #f39c12; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #e67e22; }"
        )
        self.support_btn.clicked.connect(self._open_donation)
        button_layout.addWidget(self.support_btn)

        layout.addLayout(button_layout)

        # Status bar
        self.statusBar().showMessage("Ready — Click 'Start Server' to begin")

    # ─── Tray Icon ───────────────────────────────────────────────────────

    def setup_tray_icon(self):
        """Setup system tray icon"""
        self.tray = TrayIcon(self)
        self.tray.show_requested.connect(self.show)
        self.tray.hide_requested.connect(self.hide)
        self.tray.quit_requested.connect(self.quit_application)
        self.tray.server_toggle_requested.connect(self._toggle_server)
        self.tray.show()

        self.tray.update_status("Server stopped")

    # ─── Server Lifecycle ────────────────────────────────────────────────

    def _toggle_server(self):
        """Toggle server start/stop."""
        if self._server_running:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        """Start the server in its background thread."""
        if self._server_running:
            return

        logger.info("Starting server...")
        self._update_server_ui("starting")

        try:
            self.server_thread.start()
            self._server_running = True
            self._update_server_ui("running")
            self._generate_qr_code()
            logger.info("Server started successfully")
        except Exception as e:
            logger.error(f"Failed to start server: {e}", exc_info=True)
            self._update_server_ui("stopped")
            QMessageBox.critical(self, "Error", f"Failed to start server:\n{e}")

    def _stop_server(self):
        """Stop the server."""
        if not self._server_running:
            return

        logger.info("Stopping server...")
        self._update_server_ui("stopping")

        try:
            self.server.stop()
            self.server_thread.stop()
            self.server_thread.quit()
            if not self.server_thread.wait(5000):
                logger.warning("Server thread did not stop in time, terminating")
                self.server_thread.terminate()
                self.server_thread.wait(2000)

            self._server_running = False
            self._update_server_ui("stopped")

            # Recreate server + thread for next start
            from core.server import NexRemoteServer
            from main import ServerThread
            self.server = NexRemoteServer(self.config)
            self.server.client_connected.connect(self.on_client_connected)
            self.server.client_disconnected.connect(self.on_client_disconnected)
            self.server_thread = ServerThread(self.server)

            self.clients_list.clear()
            logger.info("Server stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping server: {e}", exc_info=True)
            self._server_running = False
            self._update_server_ui("stopped")

    def _update_server_ui(self, state: str):
        """Update all UI elements to reflect server state."""
        if state == "running":
            self.server_btn.setText("Stop Server")
            self.server_btn.setStyleSheet(
                "QPushButton { background-color: #e74c3c; color: white; "
                "font-weight: bold; padding: 10px; border-radius: 6px; font-size: 14px; }"
                "QPushButton:hover { background-color: #c0392b; }"
            )
            self.server_btn.setEnabled(True)
            self.status_label.setText("● Server Running")
            self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 13px;")
            self.statusBar().showMessage("Server is running — waiting for connections")
            self.tray.update_status("Server running")
            self.tray.update_server_state(True)
        elif state == "starting":
            self.server_btn.setText("Starting...")
            self.server_btn.setEnabled(False)
            self.status_label.setText("● Starting Server...")
            self.status_label.setStyleSheet("color: #f39c12; font-weight: bold; font-size: 13px;")
            self.statusBar().showMessage("Starting server...")
        elif state == "stopping":
            self.server_btn.setText("Stopping...")
            self.server_btn.setEnabled(False)
            self.status_label.setText("● Stopping Server...")
            self.status_label.setStyleSheet("color: #f39c12; font-weight: bold; font-size: 13px;")
            self.statusBar().showMessage("Stopping server...")
        else:  # stopped
            self.server_btn.setText("Start Server")
            self.server_btn.setStyleSheet(
                "QPushButton { background-color: #2ecc71; color: white; "
                "font-weight: bold; padding: 10px; border-radius: 6px; font-size: 14px; }"
                "QPushButton:hover { background-color: #27ae60; }"
            )
            self.server_btn.setEnabled(True)
            self.status_label.setText("● Server Stopped")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px;")
            self.statusBar().showMessage("Ready — Click 'Start Server' to begin")
            self.tray.update_status("Server stopped")
            self.tray.update_server_state(False)

            # Clear QR code
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText("Start the server to\nshow QR code")
            self.qr_label.setStyleSheet(
                "border: 2px dashed #555; border-radius: 8px; color: #888; font-size: 13px;"
            )

    # ─── QR Code ─────────────────────────────────────────────────────────

    def _generate_qr_code(self):
        """Generate connection QR code."""
        try:
            data = {
                "host": _get_lan_ip(),
                "port": self.config.get('server_port', 8765),
                "port_insecure": self.config.get('server_port_insecure', 8766),
                "name": self.config.get('pc_name', socket.gethostname()),
                "id": self.config.get('device_id', ''),
            }

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=2,
            )
            qr.add_data(json.dumps(data))
            qr.make(fit=True)

            pil_img = qr.make_image(fill_color="black", back_color="white")

            # Convert PIL → QPixmap
            buffer = io.BytesIO()
            pil_img.save(buffer, format='PNG')
            buffer.seek(0)
            qimage = QImage.fromData(buffer.read())
            pixmap = QPixmap.fromImage(qimage)

            self.qr_label.setPixmap(
                pixmap.scaled(
                    self.qr_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.qr_label.setStyleSheet("border: none;")

            logger.info(f"QR code generated for {data['host']}:{data['port']}")
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}", exc_info=True)
            self.qr_label.setText("QR code error")

    # ─── Client Events ───────────────────────────────────────────────────

    @pyqtSlot(str, str)
    def on_client_connected(self, client_id: str, device_name: str):
        """Handle client connection"""
        item = QListWidgetItem(f"{device_name} ({client_id[:8]}...)")
        item.setData(Qt.ItemDataRole.UserRole, client_id)
        self.clients_list.addItem(item)

        self.statusBar().showMessage(f"Device connected: {device_name}")

        self.tray.show_message(
            "Device Connected",
            f"{device_name} has connected",
            duration=3000,
        )
        self.tray.update_client_count(self.clients_list.count())

    @pyqtSlot(str)
    def on_client_disconnected(self, client_id: str):
        """Handle client disconnection"""
        for i in range(self.clients_list.count()):
            item = self.clients_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == client_id:
                self.clients_list.takeItem(i)
                break

        self.statusBar().showMessage("Device disconnected")
        self.tray.update_client_count(self.clients_list.count())

    # ─── Dialogs ─────────────────────────────────────────────────────────

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            logger.info("Settings updated")
            # Refresh port / IP labels
            port = self.config.get('server_port', 8765)
            port_insecure = self.config.get('server_port_insecure', 8766)
            self.port_label.setText(f"Ports: {port} (secure) / {port_insecure} (fallback)")
            self.ip_label.setText(f"LAN IP: {_get_lan_ip()}")
            self.pc_info_label.setText(f"PC Name: {self.config.get('pc_name', 'Unknown PC')}")

            # Regenerate QR if server is running
            if self._server_running:
                self._generate_qr_code()

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About NexRemote",
            "<h2>NexRemote</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A complete PC remote control application supporting "
            "gamepad, keyboard, mouse, screen sharing, camera, and more.</p>"
            "<hr>"
            "<p><b>Developer:</b> Neural Nexus Studios</p>"
            "<p>NexRemote is free and ad-free. If you find it useful, "
            "please consider supporting development:</p>"
            '<p><a href="https://buymeacoffee.com/avishake69">'
            "☕ Buy Me a Coffee</a></p>",
        )

    def _open_donation(self):
        """Open donation URL in default browser."""
        QDesktopServices.openUrl(QUrl("https://buymeacoffee.com/avishake69"))

    # ─── Window Events ───────────────────────────────────────────────────

    def quit_application(self):
        """Quit the application"""
        logger.info("Quit requested from tray/menu")

        if self._server_running:
            self._stop_server()

        try:
            self.tray.hide()
        except Exception:
            pass

        QApplication.quit()

        # Force exit after a short delay if Qt didn't close everything
        import threading

        def force_exit():
            import time
            time.sleep(3)
            logger.warning("Force exiting — cleanup timeout")
            os._exit(0)

        threading.Thread(target=force_exit, daemon=True).start()

    def closeEvent(self, event):
        """Handle window close event — minimize to tray"""
        event.ignore()
        self.hide()

        self.tray.show_message(
            "NexRemote",
            "Application minimized to system tray",
            duration=2000,
        )