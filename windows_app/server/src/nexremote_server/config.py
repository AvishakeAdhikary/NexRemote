"""Runtime configuration and data-folder resolution."""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
from dataclasses import dataclass
from pathlib import Path


def current_package_family_name() -> str | None:
    """Return the MSIX package family name when running inside a package, else None."""
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        length = ctypes.c_uint32(0)
        # ERROR_INSUFFICIENT_BUFFER (122) means we are packaged; APPMODEL_ERROR_NO_PACKAGE (15700) means not.
        rc = kernel32.GetCurrentPackageFamilyName(ctypes.byref(length), None)
        if rc != 122:
            return None
        buffer = ctypes.create_unicode_buffer(length.value)
        if kernel32.GetCurrentPackageFamilyName(ctypes.byref(length), buffer) != 0:
            return None
        return buffer.value or None
    except (AttributeError, OSError):
        return None


def default_data_dir() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    family = current_package_family_name()
    if family:
        # Same folder ApplicationData.Current.LocalFolder resolved to for the WinUI host,
        # so the Store update can import that host's settings, certificate and trusted devices.
        return local / "Packages" / family / "LocalState"
    return local / "NexRemote"


@dataclass(slots=True)
class Config:
    data_dir: Path
    control_host: str = "127.0.0.1"
    control_port: int = 51888
    control_token: str | None = None
    dev: bool = False
    autostart_server: bool = True
    log_level: str = "INFO"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "nexremote.db"

    @property
    def certs_dir(self) -> Path:
        return self.data_dir / "certs"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def tools_dir(self) -> Path:
        return self.data_dir / "tools"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.certs_dir, self.logs_dir, self.tools_dir):
            path.mkdir(parents=True, exist_ok=True)


def parse_args(argv: list[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(prog="nexremote-server")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--control-port", type=int, default=51888)
    parser.add_argument("--control-token", default=os.environ.get("NEXREMOTE_CONTROL_TOKEN"))
    parser.add_argument("--dev", action="store_true", help="development mode (control API without token)")
    parser.add_argument("--no-autostart", action="store_true", help="do not start protocol listeners at boot")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    if not args.dev and not args.control_token:
        parser.error("--control-token is required outside --dev mode")

    return Config(
        data_dir=(args.data_dir or default_data_dir()).resolve(),
        control_port=args.control_port,
        control_token=None if args.dev else args.control_token,
        dev=args.dev,
        autostart_server=not args.no_autostart,
        log_level=args.log_level.upper(),
    )
