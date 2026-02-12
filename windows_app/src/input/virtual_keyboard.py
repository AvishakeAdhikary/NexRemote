"""
Virtual Keyboard Implementation
Simulates keyboard input using pynput
"""
from pynput.keyboard import Controller, Key
from utils.logger import get_logger

logger = get_logger(__name__)

class VirtualKeyboard:
    """Virtual keyboard controller"""
    
    def __init__(self):
        self.keyboard = Controller()
        
        # Key mapping
        self.special_keys = {
            'enter': Key.enter,
            'backspace': Key.backspace,
            'tab': Key.tab,
            'space': Key.space,
            'esc': Key.esc,
            'shift': Key.shift,
            'ctrl': Key.ctrl,
            'alt': Key.alt,
            'cmd': Key.cmd,
            'caps_lock': Key.caps_lock,
            'delete': Key.delete,
            'end': Key.end,
            'home': Key.home,
            'page_up': Key.page_up,
            'page_down': Key.page_down,
            'left': Key.left,
            'right': Key.right,
            'up': Key.up,
            'down': Key.down,
            'f1': Key.f1,
            'f2': Key.f2,
            'f3': Key.f3,
            'f4': Key.f4,
            'f5': Key.f5,
            'f6': Key.f6,
            'f7': Key.f7,
            'f8': Key.f8,
            'f9': Key.f9,
            'f10': Key.f10,
            'f11': Key.f11,
            'f12': Key.f12,
        }
        
        logger.info("Virtual keyboard initialized")
    
    def send_key(self, data: dict):
        """Send keyboard input"""
        try:
            action = data.get('action')
            
            if action == 'type':
                self._type_text(data.get('text', ''))
            elif action == 'press':
                self._press_key(data.get('key'))
            elif action == 'release':
                self._release_key(data.get('key'))
            elif action == 'hotkey':
                self._send_hotkey(data.get('keys', []))
                
        except Exception as e:
            logger.error(f"Error sending keyboard input: {e}")
    
    def _type_text(self, text: str):
        """Type text string"""
        self.keyboard.type(text)
    
    def _press_key(self, key: str):
        """Press a key"""
        if key in self.special_keys:
            self.keyboard.press(self.special_keys[key])
        elif len(key) == 1:
            self.keyboard.press(key)
    
    def _release_key(self, key: str):
        """Release a key"""
        if key in self.special_keys:
            self.keyboard.release(self.special_keys[key])
        elif len(key) == 1:
            self.keyboard.release(key)
    
    def _send_hotkey(self, keys: list):
        """Send key combination (e.g., Ctrl+C)"""
        # Press all keys
        key_objects = []
        for key in keys:
            if key in self.special_keys:
                key_obj = self.special_keys[key]
            else:
                key_obj = key
            key_objects.append(key_obj)
            self.keyboard.press(key_obj)
        
        # Release all keys in reverse order
        for key_obj in reversed(key_objects):
            self.keyboard.release(key_obj)