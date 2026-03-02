"""
Elevation utilities — run operations under Windows UAC.

The main application NEVER runs as admin.  When a specific operation needs
elevation (firewall rules, killing a protected process, etc.) we spawn a
short-lived Python script (`elevated_ops.py`) via the Windows `runas` verb,
which shows the standard UAC consent dialog to the user.
"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Admin check
# ---------------------------------------------------------------------------

def is_admin() -> bool:
    """Return True if the current process is running with admin privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Elevated operation runner
# ---------------------------------------------------------------------------

def _get_elevated_ops_script() -> str:
    """Return the absolute path to ``elevated_ops.py``."""
    if getattr(sys, 'frozen', False):
        # In a frozen build, elevated_ops.py lives inside the MEIPASS bundle
        return str(Path(sys._MEIPASS) / 'utils' / 'elevated_ops.py')  # type: ignore
    return str(Path(__file__).resolve().parent / 'elevated_ops.py')


def run_elevated(*args: str, wait: bool = True, timeout: int = 30) -> dict:
    """
    Launch ``elevated_ops.py`` with the given CLI arguments under a UAC
    prompt.

    In a frozen (PyInstaller) build the main exe is re-launched with a
    ``--run-elevated`` prefix instead, so no separate Python interpreter is
    needed.

    Parameters
    ----------
    *args : str
        Command-line arguments forwarded to ``elevated_ops.py``.
        Example: ``run_elevated("--firewall-add", "--port", "8765")``
    wait : bool
        If True (default), block until the elevated process finishes and
        return its exit status / result.
    timeout : int
        Maximum seconds to wait for the result when *wait* is True.

    Returns
    -------
    dict
        ``{'success': bool, 'message': str, 'detail': str | None}``
        If the user declines the UAC prompt, ``success`` is ``False`` and
        ``message`` explains what happened.
    """
    # Temp file for the elevated process to write its JSON result into.
    result_file = Path(tempfile.mktemp(suffix=".json", prefix="nexremote_elev_"))

    logger.info(f"Requesting UAC elevation for: {' '.join(args)}")

    try:
        if getattr(sys, 'frozen', False):
            # ── Frozen exe: re-launch OURSELVES with --run-elevated ────
            exe = sys.executable  # NexRemote.exe
            cmd_args_str = ' '.join(
                f'"{a}"' for a in [
                    '--run-elevated',
                    '--result-file', str(result_file),
                    *args,
                ]
            )
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, 'runas', exe, cmd_args_str, None, 0,
            )
        else:
            # ── Dev mode: launch elevated_ops.py with the Python interpreter
            script = _get_elevated_ops_script()
            if not os.path.isfile(script):
                return {
                    'success': False,
                    'message': 'Elevated helper script not found.',
                    'detail': script,
                }

            python = sys.executable
            cmd_args = [
                script,
                '--result-file', str(result_file),
                *args,
            ]
            cmd_args_str = ' '.join(f'"{a}"' for a in cmd_args)

            ret = ctypes.windll.shell32.ShellExecuteW(
                None,       # hwnd
                'runas',    # verb — triggers UAC
                python,     # executable
                cmd_args_str,  # parameters
                None,       # working directory
                0,          # SW_HIDE
            )

        if ret <= 32:
            # User declined UAC or some other shell error.
            logger.warning(f"UAC elevation declined or failed (code {ret})")
            return {
                "success": False,
                "message": "Elevation was declined by the user.",
                "detail": f"ShellExecuteW returned {ret}",
            }

        if not wait:
            return {
                "success": True,
                "message": "Elevated process launched (not waiting for result).",
                "detail": None,
            }

        # Poll for the result file produced by the elevated process.
        import time
        elapsed = 0.0
        poll_interval = 0.25
        while elapsed < timeout:
            if result_file.exists():
                try:
                    data = json.loads(result_file.read_text(encoding="utf-8"))
                    result_file.unlink(missing_ok=True)
                    logger.info(f"Elevated operation result: {data}")
                    return data
                except (json.JSONDecodeError, OSError):
                    pass  # file not fully written yet — retry
            time.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning("Timed out waiting for elevated operation result.")
        return {
            "success": False,
            "message": "Timed out waiting for the elevated operation to complete.",
            "detail": None,
        }

    except Exception as e:
        logger.error(f"Failed to request elevation: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to request elevation: {e}",
            "detail": None,
        }
    finally:
        # Best-effort cleanup.
        result_file.unlink(missing_ok=True)
