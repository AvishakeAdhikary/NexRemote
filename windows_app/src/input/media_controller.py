"""
Media Controller
Controls Windows media playback and system volume using Win32 API
"""
import ctypes
from ctypes import wintypes
from utils.logger import get_logger

logger = get_logger(__name__)

# Win32 constants
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_STOP = 0xB2
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

user32 = ctypes.windll.user32

class MediaController:
    """Windows media playback controller using Win32 API"""
    
    def __init__(self):
        logger.info("Media controller initialized")
    
    def send_command(self, data: dict):
        """Send media control command"""
        try:
            action = data.get('action')
            
            if action == 'play' or action == 'pause':
                self._press_media_key(VK_MEDIA_PLAY_PAUSE)
            elif action == 'stop':
                self._press_media_key(VK_MEDIA_STOP)
            elif action == 'next':
                self._press_media_key(VK_MEDIA_NEXT_TRACK)
            elif action == 'previous':
                self._press_media_key(VK_MEDIA_PREV_TRACK)
            elif action == 'volume':
                self._set_volume(data.get('value', 50))
            elif action == 'mute_toggle':
                self._press_media_key(VK_VOLUME_MUTE)
            elif action == 'volume_up':
                self._press_media_key(VK_VOLUME_UP)
            elif action == 'volume_down':
                self._press_media_key(VK_VOLUME_DOWN)
            elif action == 'seek':
                logger.info(f"Seek requested: {data.get('position')}")
            elif action == 'get_info':
                return self._get_media_info()
            else:
                logger.warning(f"Unknown media action: {action}")
                
        except Exception as e:
            logger.error(f"Error sending media command: {e}", exc_info=True)
    
    def _press_media_key(self, vk_code: int):
        """Press and release a media/volume key using Win32 keybd_event"""
        try:
            # Key down
            user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
            # Key up
            user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            logger.info(f"Pressed media key: {hex(vk_code)}")
        except Exception as e:
            logger.error(f"Error pressing media key {hex(vk_code)}: {e}")
    
    def _set_volume(self, volume: int):
        """Set system volume (0-100) using pycaw or fallback to volume keys"""
        try:
            # Try pycaw for precise control
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            
            # pycaw volume is in dB scale, use scalar (0.0 to 1.0)
            scalar = max(0.0, min(1.0, volume / 100.0))
            volume_interface.SetMasterVolumeLevelScalar(scalar, None)
            logger.info(f"Volume set to {volume}% (scalar: {scalar})")
            
        except ImportError:
            # Fallback: use volume keys to approximate
            logger.warning("pycaw not available, using volume key fallback")
            self._volume_key_fallback(volume)
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            self._volume_key_fallback(volume)
    
    def _volume_key_fallback(self, target_volume: int):
        """Approximate volume control using volume up/down keys"""
        try:
            # Mute first, then press volume up repeatedly
            # Each VK_VOLUME_UP is roughly 2% increase
            import time
            
            # First mute, then unmute to reset
            user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
            
            # Press volume up proportionally (each press ≈ 2%)
            presses = target_volume // 2
            for _ in range(presses):
                user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY, 0)
                user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                time.sleep(0.02)
            
            logger.info(f"Volume set via key fallback: ~{target_volume}%")
        except Exception as e:
            logger.error(f"Volume key fallback failed: {e}")
    
    def _get_media_info(self) -> dict:
        """Get current media information"""
        result = {
            'type': 'media_control',
            'action': 'media_info',
            'title': 'Unknown',
            'artist': '',
            'duration': 0,
            'position': 0,
            'is_playing': False
        }
        
        # Try to get current volume
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            
            current_volume = volume_interface.GetMasterVolumeLevelScalar()
            is_muted = volume_interface.GetMute()
            result['volume'] = round(current_volume * 100)
            result['is_muted'] = bool(is_muted)
        except Exception:
            result['volume'] = -1
            result['is_muted'] = False
        
        return result
