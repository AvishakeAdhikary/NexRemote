"""
ViGEmBus Driver detection and installation guidance.

The vgamepad package requires the ViGEmBus kernel driver to be installed
system-wide.  This module detects whether it's present and provides helpers
to guide the user to install it.

ViGEmBus is treated as an **external dependency** — not bundled or auto-
installed — to keep Microsoft Store compliance clean.
"""
import subprocess
import sys
import webbrowser
from utils.logger import get_logger

logger = get_logger(__name__)

# Official release page for ViGEmBus driver
VIGEM_DOWNLOAD_URL = "https://github.com/nefarius/ViGEmBus/releases/latest"
VIGEM_GUIDE_URL = "https://vigem.org/projects/ViGEm/How-to-Install/"


def is_vigem_installed() -> bool:
    """
    Check if the ViGEmBus kernel driver is installed.

    Queries the Windows Service Control Manager for the ``ViGEmBus`` service.
    Returns True if the service exists (regardless of running state).
    """
    if sys.platform != "win32":
        return False

    try:
        result = subprocess.run(
            ["sc.exe", "query", "ViGEmBus"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # sc.exe returns 0 if the service exists
        installed = result.returncode == 0
        logger.info(f"ViGEmBus driver installed: {installed}")
        return installed
    except Exception as e:
        logger.warning(f"Could not check ViGEmBus status: {e}")
        return False


def open_vigem_download():
    """Open the ViGEmBus download page in the default browser."""
    logger.info(f"Opening ViGEmBus download page: {VIGEM_DOWNLOAD_URL}")
    webbrowser.open(VIGEM_DOWNLOAD_URL)


def open_vigem_guide():
    """Open the ViGEm installation guide in the default browser."""
    logger.info(f"Opening ViGEm install guide: {VIGEM_GUIDE_URL}")
    webbrowser.open(VIGEM_GUIDE_URL)
