import pyautogui
import logging

logger = logging.getLogger(__name__)

# Disable pyautogui failsafe
pyautogui.FAILSAFE = False

class MouseController:
    """Controls mouse input"""
    
    def __init__(self):
        self.sensitivity = 1.0
        
    def move(self, dx, dy):
        """Move mouse cursor relative to current position"""
        try:
            current_x, current_y = pyautogui.position()
            new_x = current_x + int(dx * self.sensitivity)
            new_y = current_y + int(dy * self.sensitivity)
            pyautogui.moveTo(new_x, new_y)
        except Exception as e:
            logger.error(f"Mouse move error: {e}")
    
    def click(self, button='left', double=False):
        """Click mouse button"""
        try:
            if double:
                pyautogui.doubleClick(button=button)
            else:
                pyautogui.click(button=button)
        except Exception as e:
            logger.error(f"Mouse click error: {e}")
    
    def scroll(self, dx, dy):
        """Scroll mouse wheel"""
        try:
            if dy != 0:
                pyautogui.scroll(int(dy))
            if dx != 0:
                pyautogui.hscroll(int(dx))
        except Exception as e:
            logger.error(f"Mouse scroll error: {e}")
    
    def drag(self, dx, dy, button='left'):
        """Drag mouse"""
        try:
            current_x, current_y = pyautogui.position()
            pyautogui.drag(dx, dy, button=button)
        except Exception as e:
            logger.error(f"Mouse drag error: {e}")