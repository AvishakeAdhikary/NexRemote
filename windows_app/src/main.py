"""
NexRemote - Windows Application
Main entry point. The GUI application owns the entire lifecycle.
The server runs in a background thread and can be started/stopped from the UI.
"""
import sys
import os
import ctypes
import atexit
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from utils.paths import get_assets_dir, is_frozen

# Set Windows AppUserModelID BEFORE creating QApplication
# This ensures taskbar grouping, notifications, and UAC prompts show "NexRemote"
if sys.platform == 'win32':
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'NeuralNexusStudios.NexRemote'
        )
    except Exception:
        pass

from ui.main_window import MainWindow
from core.server import NexRemoteServer
from core.server_thread import ServerThread
from utils.logger import setup_logger
from utils.config import Config
from security.firewall_config import configure_firewall

logger = setup_logger()


def main():
    """Application entry point"""
    try:
        # Initialize Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("NexRemote")
        app.setOrganizationName("NeuralNexusStudios")
        app.setApplicationDisplayName("NexRemote")

        # Set application icon globally
        assets = get_assets_dir()
        ico_path = assets / 'images' / 'logo.ico'
        png_path = assets / 'images' / 'logo.png'
        icon_path = str(ico_path if ico_path.exists() else png_path)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        # Prevent Qt from quitting when all windows are hidden (tray mode)
        app.setQuitOnLastWindowClosed(False)

        # Load configuration
        config = Config()

        # Configure Windows Firewall (best-effort)
        logger.info("Configuring firewall rules...")
        if not configure_firewall():
            logger.warning(
                "Failed to configure firewall automatically. "
                "Manual configuration may be needed."
            )

        # Initialize server (does NOT start yet — MainWindow controls lifecycle)
        server = NexRemoteServer(config)

        # Create server thread (not started yet)
        server_thread = ServerThread(server)

        # Create main window — it owns the server start/stop lifecycle
        main_window = MainWindow(server, server_thread, config)
        main_window.show()

        logger.info("Application started successfully")

        # One-shot cleanup guard: prevents double-call from atexit + aboutToQuit.
        # Note: we delegate to main_window (which always has the CURRENT server_thread)
        # because _stop_server() recreates the thread on each stop, making any direct
        # reference to server_thread in this closure go stale.
        _cleaned_up = False

        def cleanup():
            nonlocal _cleaned_up
            if _cleaned_up:
                return
            _cleaned_up = True

            logger.info("Shutting down...")
            try:
                if main_window._server_running:
                    main_window._stop_server()
            except RuntimeError:
                # Qt C++ objects already deleted — nothing we can do
                pass
            except Exception as e:
                logger.warning(f"Cleanup warning (non-fatal): {e}")

        # aboutToQuit fires when QApplication.quit() is called (e.g., from tray Quit)
        app.aboutToQuit.connect(cleanup)
        # atexit fires after app.exec() returns — acts as a safety net for abnormal exits
        atexit.register(cleanup)

        # Execute application — returns exit code when tray Quit is triggered
        exit_code = app.exec()
        return exit_code

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        os._exit(1)


if __name__ == "__main__":
    sys.exit(main() or 0)
