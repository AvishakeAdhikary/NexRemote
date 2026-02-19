"""
Application paths utility.
Centralizes all data directory resolution. In production (PyInstaller frozen),
data is stored in %LOCALAPPDATA%/NexRemote. In development, data is stored
in ./data relative to the source directory.
"""
import sys
import os
from pathlib import Path

# Cached data directory
_data_dir: Path | None = None


def is_frozen() -> bool:
    """Check if running as a PyInstaller-bundled executable."""
    return getattr(sys, 'frozen', False)


def get_data_dir() -> Path:
    """
    Get the application data directory.

    Production (frozen exe): %LOCALAPPDATA%/NexRemote
    Development (python):    ./data (relative to windows_app/src)
    """
    global _data_dir
    if _data_dir is not None:
        return _data_dir

    if is_frozen():
        # Production: use standard Windows AppData location
        local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        _data_dir = Path(local_appdata) / 'NexRemote'
    else:
        # Development: use ./data relative to the src directory
        src_dir = Path(__file__).resolve().parent.parent
        _data_dir = src_dir / 'data'

    _data_dir.mkdir(parents=True, exist_ok=True)
    return _data_dir


def get_log_dir() -> Path:
    """Get the logs directory."""
    log_dir = get_data_dir() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_certs_dir() -> Path:
    """Get the certificates directory."""
    certs_dir = get_data_dir() / 'certs'
    certs_dir.mkdir(parents=True, exist_ok=True)
    return certs_dir


def get_config_file() -> Path:
    """Get the configuration file path."""
    return get_data_dir() / 'config.json'


def get_assets_dir() -> Path:
    """
    Get the assets directory.

    Production: bundled alongside the executable
    Development: src/assets
    """
    if is_frozen():
        # PyInstaller stores data files in sys._MEIPASS
        base = Path(sys._MEIPASS)  # type: ignore
    else:
        base = Path(__file__).resolve().parent.parent

    return base / 'assets'
