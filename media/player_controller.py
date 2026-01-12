from pynput.keyboard import Key, Controller
import logging

logger_media = logging.getLogger(__name__)

class MediaController:
    """Control media playback"""
    
    def __init__(self):
        self.keyboard = Controller()
        
    def play_pause(self):
        """Toggle play/pause"""
        try:
            self.keyboard.press(Key.media_play_pause)
            self.keyboard.release(Key.media_play_pause)
        except Exception as e:
            logger_media.error(f"Play/pause error: {e}")
    
    def next_track(self):
        """Next track"""
        try:
            self.keyboard.press(Key.media_next)
            self.keyboard.release(Key.media_next)
        except Exception as e:
            logger_media.error(f"Next track error: {e}")
    
    def prev_track(self):
        """Previous track"""
        try:
            self.keyboard.press(Key.media_previous)
            self.keyboard.release(Key.media_previous)
        except Exception as e:
            logger_media.error(f"Previous track error: {e}")
    
    def volume_up(self):
        """Increase volume"""
        try:
            self.keyboard.press(Key.media_volume_up)
            self.keyboard.release(Key.media_volume_up)
        except Exception as e:
            logger_media.error(f"Volume up error: {e}")
    
    def volume_down(self):
        """Decrease volume"""
        try:
            self.keyboard.press(Key.media_volume_down)
            self.keyboard.release(Key.media_volume_down)
        except Exception as e:
            logger_media.error(f"Volume down error: {e}")
    
    def mute(self):
        """Mute/unmute"""
        try:
            self.keyboard.press(Key.media_volume_mute)
            self.keyboard.release(Key.media_volume_mute)
        except Exception as e:
            logger_media.error(f"Mute error: {e}")
    
    def volume(self, value):
        """Set volume (0-100)"""
        # Note: Windows doesn't have direct volume control via keyboard
        # This is a simplified implementation
        try:
            if value > 50:
                for _ in range(5):
                    self.volume_up()
            else:
                for _ in range(5):
                    self.volume_down()
        except Exception as e:
            logger_media.error(f"Volume error: {e}")