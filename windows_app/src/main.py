"""
NexRemote - Windows Application
Main entry point. The GUI application owns the entire lifecycle.
The server runs in a background thread and can be started/stopped from the UI.
"""
import sys
import os
import ctypes
import asyncio
import atexit
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread
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
from utils.logger import setup_logger
from utils.config import Config
from security.firewall_config import configure_firewall

logger = setup_logger()


class ServerThread(QThread):
    """Thread to run async server. Owned by MainWindow for start/stop control."""

    def __init__(self, server):
        super().__init__()
        self.server = server
        self.loop = None

    def run(self):
        """Run the asyncio event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.server.start())
        except asyncio.CancelledError:
            pass
        finally:
            # Cancel all remaining tasks
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self.loop.close()

    def stop(self):
        """Stop the asyncio event loop from another thread"""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


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

        # Register cleanup for any running server
        def cleanup():
            logger.info("Shutting down...")
            if server_thread.isRunning():
                server.stop()
                server_thread.stop()
                server_thread.quit()
                if not server_thread.wait(5000):
                    logger.warning("Server thread did not stop in time, terminating")
                    server_thread.terminate()
                    server_thread.wait(2000)

        atexit.register(cleanup)
        app.aboutToQuit.connect(cleanup)

        # Execute application
        exit_code = app.exec()
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        os._exit(1)


if __name__ == "__main__":
    main()