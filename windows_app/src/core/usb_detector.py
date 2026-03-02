"""
ADB Manager — USB connection via Android Debug Bridge (ADB)
Sets up ADB port forwarding so the Flutter client can connect to
the server over USB without any network configuration.

Workflow:
1. Server detects ADB-connected devices
2. Server sets up reverse port forwarding (adb reverse tcp:PORT tcp:PORT)
   so the phone can reach the server on localhost:PORT
3. Flutter client connects to ws://localhost:PORT
"""
import platform
import subprocess
import shutil
import threading
import time
from typing import Optional, List, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

# Default ADB path — will auto-detect from PATH or common install locations
_COMMON_ADB_PATHS_WIN = [
    r"C:\platform-tools\adb.exe",
    r"C:\Android\platform-tools\adb.exe",
    r"C:\Users\{user}\AppData\Local\Android\Sdk\platform-tools\adb.exe",
]


class AdbManager:
    """Manage ADB connections for USB-based communication."""

    def __init__(self, server_port: int = 8766,
                 on_device_connected=None,
                 on_device_disconnected=None,
                 poll_interval: float = 3.0):
        """
        Args:
            server_port:         The server port to forward.
            on_device_connected: callback(serial: str, model: str)
            on_device_disconnected: callback(serial: str)
            poll_interval:       seconds between device checks.
        """
        self._server_port = server_port
        self._on_connected = on_device_connected
        self._on_disconnected = on_device_disconnected
        self._poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._known_devices: Dict[str, str] = {}  # serial → model
        self._adb_path: Optional[str] = None
        self._forwarded_devices: set = set()

    # ─── Public API ────────────────────────────────────────────────────

    @property
    def adb_available(self) -> bool:
        """Check if ADB is found on this system."""
        return self._find_adb() is not None

    def get_adb_path(self) -> Optional[str]:
        """Return the resolved ADB path, or None."""
        return self._find_adb()

    def start(self):
        """Start polling for ADB devices and setting up port forwarding."""
        if self._running:
            return
        adb = self._find_adb()
        if not adb:
            logger.warning("ADB not found — USB connection unavailable")
            return
        self._adb_path = adb
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"ADB manager started (adb={adb}, port={self._server_port})")

    def stop(self):
        """Stop polling and remove port forwards."""
        self._running = False
        # Remove all reverse port forwards
        for serial in list(self._forwarded_devices):
            self._remove_reverse(serial)
        self._forwarded_devices.clear()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("ADB manager stopped")

    def get_connected_devices(self) -> List[Dict[str, str]]:
        """Return list of currently connected ADB devices."""
        return [
            {"serial": s, "model": m}
            for s, m in self._known_devices.items()
        ]

    def setup_reverse_for_device(self, serial: str) -> bool:
        """Manually set up reverse port forwarding for a specific device."""
        return self._setup_reverse(serial)

    # ─── Internal ──────────────────────────────────────────────────────

    def _find_adb(self) -> Optional[str]:
        """Find the ADB executable."""
        if self._adb_path:
            return self._adb_path

        # Check PATH first
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            self._adb_path = adb_in_path
            return adb_in_path

        # Check common install locations (Windows)
        if platform.system() == 'Windows':
            import os
            username = os.environ.get('USERNAME', '')
            for path_template in _COMMON_ADB_PATHS_WIN:
                path = path_template.replace('{user}', username)
                if os.path.isfile(path):
                    self._adb_path = path
                    return path

        return None

    def _run_adb(self, *args, serial: Optional[str] = None,
                 timeout: int = 10) -> Optional[str]:
        """Run an ADB command and return stdout, or None on failure."""
        if not self._adb_path:
            return None

        cmd = [self._adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)

        try:
            kwargs = dict(
                capture_output=True, text=True, timeout=timeout,
            )
            if platform.system() == 'Windows':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

            proc = subprocess.run(cmd, **kwargs)
            if proc.returncode == 0:
                return proc.stdout.strip()
            else:
                logger.debug(f"ADB command failed: {' '.join(cmd)}: {proc.stderr.strip()}")
                return None
        except subprocess.TimeoutExpired:
            logger.debug(f"ADB command timed out: {' '.join(cmd)}")
            return None
        except Exception as e:
            logger.debug(f"ADB error: {e}")
            return None

    def _list_devices(self) -> Dict[str, str]:
        """List connected ADB devices. Returns {serial: model}."""
        output = self._run_adb("devices", "-l")
        if not output:
            return {}

        devices = {}
        for line in output.splitlines()[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 2 and parts[1] == 'device':
                serial = parts[0]
                model = 'Unknown'
                for part in parts[2:]:
                    if part.startswith('model:'):
                        model = part.split(':', 1)[1]
                        break
                devices[serial] = model
        return devices

    def _setup_reverse(self, serial: str) -> bool:
        """Set up reverse port forwarding: phone → server."""
        result = self._run_adb(
            "reverse",
            f"tcp:{self._server_port}",
            f"tcp:{self._server_port}",
            serial=serial,
        )
        if result is not None:
            self._forwarded_devices.add(serial)
            logger.info(f"ADB reverse port forward set for {serial} "
                        f"(tcp:{self._server_port})")
            return True
        logger.warning(f"Failed to set reverse forward for {serial}")
        return False

    def _remove_reverse(self, serial: str):
        """Remove reverse port forwarding for a device."""
        self._run_adb(
            "reverse", "--remove",
            f"tcp:{self._server_port}",
            serial=serial,
        )
        self._forwarded_devices.discard(serial)

    def _poll_loop(self):
        """Background thread: poll for device changes and maintain forwards."""
        while self._running:
            try:
                current = self._list_devices()
                current_serials = set(current.keys())
                known_serials = set(self._known_devices.keys())

                # New devices
                for serial in current_serials - known_serials:
                    model = current[serial]
                    self._known_devices[serial] = model
                    # Auto-set up reverse forwarding
                    self._setup_reverse(serial)
                    logger.info(f"ADB device connected: {model} ({serial})")
                    if self._on_connected:
                        self._on_connected(serial, model)

                # Disconnected devices
                for serial in known_serials - current_serials:
                    model = self._known_devices.pop(serial, 'Unknown')
                    self._remove_reverse(serial)
                    logger.info(f"ADB device disconnected: {model} ({serial})")
                    if self._on_disconnected:
                        self._on_disconnected(serial)

            except Exception as e:
                logger.debug(f"ADB poll error: {e}")

            time.sleep(self._poll_interval)
