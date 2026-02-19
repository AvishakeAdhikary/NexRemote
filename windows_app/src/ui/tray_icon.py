"""
System Tray Icon
Provides system tray integration for the application
"""
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal
from utils.logger import get_logger
from utils.paths import get_assets_dir

logger = get_logger(__name__)


class TrayIcon(QObject):
    """System tray icon with menu"""

    show_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    server_toggle_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tray_icon = QSystemTrayIcon(parent)
        self.tray_icon.setToolTip("NexRemote")

        # Set icon from local assets
        assets = get_assets_dir()
        ico_path = assets / 'images' / 'logo.ico'
        png_path = assets / 'images' / 'logo.png'
        icon_file = str(ico_path if ico_path.exists() else png_path)
        if os.path.exists(icon_file):
            self.tray_icon.setIcon(QIcon(icon_file))

        self._server_running = False
        self.create_menu()
        self.tray_icon.activated.connect(self.on_activated)

        logger.info("System tray icon initialized")

    def create_menu(self):
        """Create tray icon context menu"""
        menu = QMenu()

        # Show action
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_requested.emit)
        menu.addAction(show_action)

        # Hide action
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide_requested.emit)
        menu.addAction(hide_action)

        menu.addSeparator()

        # Server toggle action
        self.server_action = QAction("Start Server", self)
        self.server_action.triggered.connect(self.server_toggle_requested.emit)
        menu.addAction(self.server_action)

        # Status action (informational)
        self.status_action = QAction("Status: Server stopped", self)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def on_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()

    def show(self):
        """Show the tray icon"""
        self.tray_icon.show()
        logger.debug("Tray icon shown")

    def hide(self):
        """Hide the tray icon"""
        self.tray_icon.hide()
        logger.debug("Tray icon hidden")

    def show_message(
        self,
        title: str,
        message: str,
        icon=QSystemTrayIcon.MessageIcon.Information,
        duration: int = 3000,
    ):
        """Show notification message"""
        if self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, icon, duration)
            logger.debug(f"Notification shown: {title} - {message}")

    def update_status(self, status: str):
        """Update status in menu"""
        self.status_action.setText(f"Status: {status}")

    def update_server_state(self, running: bool):
        """Update the server toggle action text."""
        self._server_running = running
        self.server_action.setText("Stop Server" if running else "Start Server")

    def update_client_count(self, count: int):
        """Update connected clients count"""
        if count == 0:
            self.update_status("No clients connected")
        elif count == 1:
            self.update_status("1 client connected")
        else:
            self.update_status(f"{count} clients connected")