"""
Media Controller — Production-grade Windows media state sync.

Architecture
------------
* A single **_ComWorker** thread owns ALL COM objects for the application's
  lifetime.  It is initialized with CoInitialize() (STA) once and never
  uninitializes, so comtypes' __del__ always finds a valid apartment.

* `cast()` is intentionally NOT used for IAudioEndpointVolume pointers.
  Instead, `QueryInterface()` is used, which calls AddRef() on the new pointer,
  so the ref-count is always correct and Release() never over-decrements.

* SMTC (System Media Transport Controls) is queried via PowerShell using the
  [Type, Assembly, ContentType=WindowsRuntime] load pattern + synchronous
  Status polling — significantly more reliable than the AsTask / reflection
  approach in non-interactive shells.
"""
import queue
import threading
import concurrent.futures
import subprocess
import json as _json
import ctypes
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Win32 virtual-key constants ────────────────────────────────────────────────
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
VK_MEDIA_PLAY_PAUSE   = 0xB3
VK_MEDIA_STOP         = 0xB2
VK_MEDIA_NEXT_TRACK   = 0xB0
VK_MEDIA_PREV_TRACK   = 0xB1
VK_VOLUME_MUTE        = 0xAD
VK_VOLUME_DOWN        = 0xAE
VK_VOLUME_UP          = 0xAF

user32 = ctypes.windll.user32


# ── Dedicated COM thread ───────────────────────────────────────────────────────

class _ComWorker:
    """
    Singleton background thread that owns all COM/pycaw operations.

    Why a dedicated thread instead of a context manager?
    ----------------------------------------------------
    asyncio's thread-pool threads are recycled.  comtypes auto-initializes COM
    on the first use per thread, and our previous _com_scope() then called
    CoUninitialize() — decrementing the ref count below what comtypes expected.
    Subsequent GC runs then tried Release() on already-freed COM objects,
    producing the "access violation reading 0xFFFFFFFFFFFFFFFF" error.

    A single persistent STA thread avoids all of that:
    • CoInitialize() called once — never uninitialized
    • All COM objects are created *and* GC'd on the same thread
    • Thread is daemon → process exit cleans it up naturally
    """
    _instance: '_ComWorker | None' = None
    _lock = threading.Lock()

    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="COM-Worker",
        )
        self._thread.start()

    @classmethod
    def get(cls) -> '_ComWorker':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _run(self):
        """Main loop — runs forever on the dedicated COM thread."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception as e:
            logger.error(f"COM thread: CoInitialize failed: {e}")

        while True:
            fn, future = self._q.get()
            if fn is None:
                break
            try:
                result = fn()
                if not future.done():
                    future.set_result(result)
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)

    def submit(self, fn) -> concurrent.futures.Future:
        """Submit a no-arg callable to the COM thread. Returns a Future."""
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self._q.put((fn, fut))
        return fut

    def run_sync(self, fn, timeout: float = 5.0):
        """Submit and block until result (or raise on timeout/exception)."""
        return self.submit(fn).result(timeout=timeout)


# ── Volume / mute via pycaw (COM thread only) ─────────────────────────────────

def _com_get_volume_state() -> dict:
    """
    MUST be called from the COM thread.
    Returns {'volume': 0–100, 'is_muted': bool}.
    Uses QueryInterface() — NOT cast() — to avoid double-Release access violations.
    """
    result = {'volume': -1, 'is_muted': False}
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        devices = AudioUtilities.GetSpeakers()
        # Activate() returns a raw IUnknown.  QueryInterface does AddRef → safe.
        raw = devices._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol_iface = raw.QueryInterface(IAudioEndpointVolume)
        try:
            result['volume'] = round(vol_iface.GetMasterVolumeLevelScalar() * 100)
            result['is_muted'] = bool(vol_iface.GetMute())
        finally:
            del vol_iface  # Release via QueryInterface's ref
            del raw        # Release via Activate's ref
    except Exception as e:
        logger.debug(f"COM volume read failed: {e}")
    return result


def _com_set_volume(volume: int):
    """MUST be called from the COM thread."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        devices = AudioUtilities.GetSpeakers()
        raw = devices._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol_iface = raw.QueryInterface(IAudioEndpointVolume)
        try:
            vol_iface.SetMasterVolumeLevelScalar(max(0.0, min(1.0, volume / 100.0)), None)
            logger.info(f"Volume set to {volume}%")
        finally:
            del vol_iface
            del raw
    except Exception as e:
        logger.error(f"COM set volume failed: {e}")
        # Fallback handled by caller


def _com_toggle_mute():
    """MUST be called from the COM thread."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        devices = AudioUtilities.GetSpeakers()
        raw = devices._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol_iface = raw.QueryInterface(IAudioEndpointVolume)
        try:
            current = bool(vol_iface.GetMute())
            vol_iface.SetMute(not current, None)
            logger.info(f"Mute {'enabled' if not current else 'disabled'}")
        finally:
            del vol_iface
            del raw
    except Exception as e:
        logger.debug(f"COM mute toggle failed ({e}), falling back to key")
        user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


# ── SMTC via PowerShell (no WinRT package required) ──────────────────────────

# Uses [Type, Assembly, ContentType=WindowsRuntime] load syntax + synchronous
# Status polling instead of the unreliable AsTask/reflection pattern.
_SMTC_PS = r"""
$ErrorActionPreference = 'Stop'
try {
    # Load the WinRT type in PowerShell 5+ style
    $null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,
             Windows.Media.Control, ContentType=WindowsRuntime]
    $null = [Windows.Foundation.AsyncStatus, Windows.Foundation, ContentType=WindowsRuntime]

    $op = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
    $waited = 0
    while ($op.Status -eq [Windows.Foundation.AsyncStatus]::Started -and $waited -lt 3000) {
        [System.Threading.Thread]::Sleep(50); $waited += 50
    }
    if ($op.Status -ne [Windows.Foundation.AsyncStatus]::Completed) {
        '{"title":"","artist":"","is_playing":false,"has_media":false}'; exit 0
    }
    $mgr = $op.GetResults()
    $session = $mgr.GetCurrentSession()
    if ($null -eq $session) {
        '{"title":"","artist":"","is_playing":false,"has_media":false}'; exit 0
    }

    $propOp = $session.TryGetMediaPropertiesAsync()
    $waited = 0
    while ($propOp.Status -eq [Windows.Foundation.AsyncStatus]::Started -and $waited -lt 2000) {
        [System.Threading.Thread]::Sleep(50); $waited += 50
    }
    $props = $propOp.GetResults()

    $playback = $session.GetPlaybackInfo()
    $null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus,
             Windows.Media.Control, ContentType=WindowsRuntime]
    $isPlaying = ($playback.PlaybackStatus -eq
        [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus]::Playing)

    [PSCustomObject]@{
        title      = if ($null -ne $props -and $props.Title)  { $props.Title }  else { '' }
        artist     = if ($null -ne $props -and $props.Artist) { $props.Artist } else { '' }
        is_playing = [bool]$isPlaying
        has_media  = $true
    } | ConvertTo-Json -Compress
} catch {
    '{"title":"","artist":"","is_playing":false,"has_media":false}'
}
"""


def _get_smtc_state() -> dict:
    """
    Query SMTC via a short-lived PowerShell process.
    Returns {'title', 'artist', 'is_playing', 'has_media'}.
    """
    empty = {'title': '', 'artist': '', 'is_playing': False, 'has_media': False}
    try:
        proc = subprocess.run(
            [
                'powershell.exe',
                '-NoProfile', '-NonInteractive',
                '-WindowStyle', 'Hidden',
                '-Command', _SMTC_PS,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        stdout = proc.stdout.strip()
        if stdout:
            data = _json.loads(stdout)
            return data
    except Exception as e:
        logger.debug(f"SMTC query failed: {e}")
    return empty


# ── MediaController ───────────────────────────────────────────────────────────

class MediaController:
    """
    Windows media controller.

    All volume/mute operations are dispatched to the dedicated COM thread.
    SMTC queries run as a subprocess (no COM required).
    get_full_state() combines both — safe to call from asyncio.to_thread().
    """

    def __init__(self):
        # Ensure the COM worker thread is started early
        _ComWorker.get()
        logger.info("Media controller initialized")

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def send_command(self, data: dict):
        """
        Execute a media command.  Returns a response dict for 'get_info',
        None for everything else (fire-and-forget commands).
        """
        action = data.get('action')
        try:
            if action in ('play', 'pause'):
                self._key(VK_MEDIA_PLAY_PAUSE)
            elif action == 'stop':
                self._key(VK_MEDIA_STOP)
            elif action == 'next':
                self._key(VK_MEDIA_NEXT_TRACK)
            elif action == 'previous':
                self._key(VK_MEDIA_PREV_TRACK)
            elif action == 'volume':
                self._set_volume(int(data.get('value', 50)))
            elif action == 'mute_toggle':
                _ComWorker.get().run_sync(_com_toggle_mute)
            elif action == 'volume_up':
                self._key(VK_VOLUME_UP)
            elif action == 'volume_down':
                self._key(VK_VOLUME_DOWN)
            elif action == 'seek':
                logger.info(f"Seek: {data.get('position')}")
            elif action == 'get_info':
                return self.get_full_state()
            else:
                logger.warning(f"Unknown media action: {action}")
        except Exception as e:
            logger.error(f"send_command error ({action}): {e}", exc_info=True)
        return None

    def get_full_state(self) -> dict:
        """
        Collect and return the complete current media state from Windows.
        Safe to call from any thread — COM work goes to the COM worker,
        SMTC subprocess is plain Python.
        """
        # Run COM read and SMTC query concurrently using threading
        com_future = _ComWorker.get().submit(_com_get_volume_state)
        smtc = _get_smtc_state()   # blocking subprocess call on calling thread

        try:
            vol = com_future.result(timeout=5)
        except Exception as e:
            logger.debug(f"Volume read timeout/error: {e}")
            vol = {'volume': -1, 'is_muted': False}

        title = smtc.get('title', '') or ('Now Playing' if smtc.get('has_media') else 'No Media Playing')

        return {
            'type': 'media_control',
            'action': 'media_info',
            'volume': vol['volume'],
            'is_muted': vol['is_muted'],
            'title': title,
            'artist': smtc.get('artist', ''),
            'is_playing': smtc.get('is_playing', False),
            'has_media': smtc.get('has_media', False),
            'position': 0,
            'duration': 0,
        }

    # ── Internals ──────────────────────────────────────────────────────────────

    def _key(self, vk: int):
        """Press and release a virtual media/volume key."""
        try:
            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            logger.debug(f"Media key: {hex(vk)}")
        except Exception as e:
            logger.error(f"keybd_event({hex(vk)}) failed: {e}")

    def _set_volume(self, volume: int):
        """Set volume via COM worker, fall back to key-presses if it fails."""
        try:
            _ComWorker.get().run_sync(lambda: _com_set_volume(volume))
        except Exception:
            self._volume_key_fallback(volume)

    def _volume_key_fallback(self, target: int):
        """Last-resort volume by key-presses."""
        import time
        try:
            for _ in range(2):
                user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
                user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                time.sleep(0.05)
            for _ in range(target // 2):
                user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY, 0)
                user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                time.sleep(0.02)
            logger.info(f"Volume key fallback: ~{target}%")
        except Exception as e:
            logger.error(f"Volume key fallback failed: {e}")

    def _get_media_info(self) -> dict:
        """Alias for backwards compatibility."""
        return self.get_full_state()
