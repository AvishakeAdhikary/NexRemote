"""
NexRemote - Windows Application
Main entry point. The GUI application owns the entire lifecycle.
The server runs in a background thread and can be started/stopped from the UI.

This application runs as a **standard user**.  Operations that require admin
privileges (firewall rules, killing protected processes) are elevated on
demand via the Windows UAC dialog — see ``utils/elevate.py``.
"""
import sys
import os
import ctypes
import atexit
import multiprocessing
from datetime import datetime

# ── CRITICAL: Required for PyInstaller frozen exes on Windows ──────────────
# Must be called at the very start, before anything else.
multiprocessing.freeze_support()

# ── Elevated sub-process entrypoint (frozen exe only) ──────────────────────
# When NexRemote.exe is launched with --run-elevated via UAC, skip the GUI
# entirely and run the elevated helper directly.
if '--run-elevated' in sys.argv:
    # Strip our flag so elevated_ops sees a clean argv
    sys.argv.remove('--run-elevated')
    from utils.elevated_ops import main as _elevated_main
    _elevated_main()
    sys.exit(0)

from PyQt6.QtWidgets import QApplication, QMessageBox
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
from ui.terms_dialog import TermsDialog
from core.server import NexRemoteServer
from core.server_thread import ServerThread
from utils.logger import setup_logger
from utils.config import Config
from security.firewall_config import configure_firewall

logger = setup_logger()


def _show_terms(app: QApplication, config: Config) -> bool:
    """
    Show the Terms & Privacy dialog if the user has not yet accepted.
    Returns True if the user has accepted (now or previously).
    """
    if config.get('terms_accepted', False):
        return True

    dlg = TermsDialog()
    result = dlg.exec()

    if result == TermsDialog.DialogCode.Accepted:
        config.set('terms_accepted', True)
        config.set('terms_accepted_at', datetime.now().isoformat())
        config.save()
        logger.info("User accepted Terms & Privacy Policy.")
        return True
    else:
        logger.info("User declined Terms & Privacy Policy — exiting.")
        return False


def _configure_firewall_first_launch(config: Config):
    """
    On first launch (or if firewall hasn't been configured yet), trigger a
    UAC prompt to set up Windows Firewall rules.  If the user declines,
    show a one-time info dialog and carry on.
    """
    if config.get('firewall_configured', False):
        return

    logger.info("First launch — requesting firewall configuration via UAC...")
    result = configure_firewall()

    if result["success"]:
        config.set('firewall_configured', True)
        config.save()
    else:
        # Don't block the app — just inform the user once.
        QMessageBox.information(
            None,
            "Firewall Configuration",
            "NexRemote could not configure Windows Firewall automatically.\n\n"
            "If you declined the permission prompt, the app will still work "
            "on your local network, but you may need to allow ports 8765–8766 "
            "(TCP) and 37020 (UDP) manually in Windows Firewall settings.\n\n"
            "You can retry from Settings → Network → Configure Firewall.",
        )


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

        # ── First-launch gate: Terms & Privacy Policy ──────────────────
        if not _show_terms(app, config):
            return 0  # user declined — clean exit

        # ── First-launch firewall setup (UAC, best-effort) ─────────────
        _configure_firewall_first_launch(config)

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
