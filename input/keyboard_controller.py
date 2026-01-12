"""
Keyboard Input Controller
"""
import logging
from pynput.keyboard import Key, Controller as KeyboardPynput

logger = logging.getLogger(__name__)

class KeyboardController:
    """Controls keyboard input"""
    
    def __init__(self):
        self.keyboard = KeyboardPynput()
        self.pressed_keys = set()
        
        # Key mapping
        self.key_map = {
            'enter': Key.enter,
            'tab': Key.tab,
            'space': Key.space,
            'backspace': Key.backspace,
            'delete': Key.delete,
            'escape': Key.esc,
            'shift': Key.shift,
            'ctrl': Key.ctrl,
            'alt': Key.alt,
            'win': Key.cmd,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'home': Key.home,
            'end': Key.end,
            'pageup': Key.page_up,
            'pagedown': Key.page_down,
            'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
            'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
            'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
        }
    
    def press(self, key):
        """Press a key"""
        try:
            key_obj = self._get_key(key)
            if key_obj:
                self.keyboard.press(key_obj)
                self.pressed_keys.add(key)
        except Exception as e:
            logger.error(f"Key press error: {e}")
    
    def release(self, key):
        """Release a key"""
        try:
            key_obj = self._get_key(key)
            if key_obj:
                self.keyboard.release(key_obj)
                self.pressed_keys.discard(key)
        except Exception as e:
            logger.error(f"Key release error: {e}")
    
    def type_text(self, text):
        """Type text string"""
        try:
            self.keyboard.type(text)
        except Exception as e:
            logger.error(f"Type text error: {e}")
    
    def _get_key(self, key_name):
        """Get key object from name"""
        key_name = key_name.lower()
        if key_name in self.key_map:
            return self.key_map[key_name]
        elif len(key_name) == 1:
            return key_name
        return None
    
    def release_all(self):
        """Release all pressed keys"""
        for key in list(self.pressed_keys):
            self.release(key)
