"""
Virtual Mouse Implementation
Simulates mouse input using pynput
"""
from pynput.mouse import Controller, Button
from utils.logger import get_logger

logger = get_logger(__name__)

class VirtualMouse:
    """Virtual mouse controller"""
    
    def __init__(self):
        self.mouse = Controller()
        logger.info("Virtual mouse initialized")
    
    def send_input(self, data: dict):
        """Send mouse input"""
        try:
            action = data.get('action')
            
            if action == 'move':
                self._move(data)
            elif action == 'move_relative':
                self._move_relative(data)
            elif action == 'click':
                self._click(data)
            elif action == 'press':
                self._press(data)
            elif action == 'release':
                self._release(data)
            elif action == 'scroll':
                self._scroll(data)
                
        except Exception as e:
            logger.error(f"Error sending mouse input: {e}")
    
    def _move(self, data: dict):
        """Move mouse to absolute position"""
        x = data.get('x', 0)
        y = data.get('y', 0)
        self.mouse.position = (x, y)
    
    def _move_relative(self, data: dict):
        """Move mouse relative to current position"""
        dx = data.get('dx', 0)
        dy = data.get('dy', 0)
        current_x, current_y = self.mouse.position
        self.mouse.position = (current_x + dx, current_y + dy)
    
    def _click(self, data: dict):
        """Click mouse button"""
        button = self._get_button(data.get('button', 'left'))
        count = data.get('count', 1)
        self.mouse.click(button, count)
    
    def _press(self, data: dict):
        """Press mouse button"""
        button = self._get_button(data.get('button', 'left'))
        self.mouse.press(button)
    
    def _release(self, data: dict):
        """Release mouse button"""
        button = self._get_button(data.get('button', 'left'))
        self.mouse.release(button)
    
    def _scroll(self, data: dict):
        """Scroll mouse wheel"""
        dx = data.get('dx', 0)
        dy = data.get('dy', 0)
        self.mouse.scroll(dx, dy)
    
    def _get_button(self, button_name: str) -> Button:
        """Convert button name to Button enum"""
        button_map = {
            'left': Button.left,
            'right': Button.right,
            'middle': Button.middle,
        }
        return button_map.get(button_name, Button.left)