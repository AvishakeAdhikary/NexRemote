"""
Virtual Gamepad Implementation
Simulates Xbox controller using vgamepad
"""
import vgamepad as vg
from utils.logger import get_logger

logger = get_logger(__name__)

class VirtualGamepad:
    """XInput virtual gamepad controller"""
    
    def __init__(self):
        try:
            self.gamepad = vg.VX360Gamepad()
            self.active = True
            logger.info("Virtual gamepad initialized")
        except Exception as e:
            logger.error(f"Failed to initialize gamepad: {e}")
            self.active = False
    
    def send_input(self, data: dict):
        """Process gamepad input"""
        if not self.active:
            return
        
        try:
            input_type = data.get('input_type')
            
            if input_type == 'button':
                self._handle_button(data)
            elif input_type == 'trigger':
                self._handle_trigger(data)
            elif input_type == 'joystick':
                self._handle_joystick(data)
            elif input_type == 'dpad':
                self._handle_dpad(data)
            
            # Update gamepad state
            self.gamepad.update()
            
        except Exception as e:
            logger.error(f"Error processing gamepad input: {e}")
    
    def _handle_button(self, data: dict):
        """Handle button press/release"""
        button = data.get('button')
        pressed = data.get('pressed', False)
        
        button_map = {
            'A': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            'B': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            'X': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            'Y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            'LB': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            'RB': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            'BACK': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            'START': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            'LS': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            'RS': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        }
        
        if button in button_map:
            if pressed:
                self.gamepad.press_button(button_map[button])
            else:
                self.gamepad.release_button(button_map[button])
    
    def _handle_trigger(self, data: dict):
        """Handle trigger input"""
        trigger = data.get('trigger')
        value = data.get('value', 0)
        
        # Convert 0-1 float to 0-255 int
        trigger_value = int(value * 255)
        
        if trigger == 'LT':
            self.gamepad.left_trigger(trigger_value)
        elif trigger == 'RT':
            self.gamepad.right_trigger(trigger_value)
    
    def _handle_joystick(self, data: dict):
        """Handle analog stick input"""
        stick = data.get('stick')
        x = data.get('x', 0.0)
        y = data.get('y', 0.0)
        
        # Convert -1 to 1 range to -32768 to 32767
        x_value = int(x * 32767)
        y_value = int(y * 32767)
        
        if stick == 'left':
            self.gamepad.left_joystick(x_value, y_value)
        elif stick == 'right':
            self.gamepad.right_joystick(x_value, y_value)
    
    def _handle_dpad(self, data: dict):
        """Handle D-pad input"""
        direction = data.get('direction')
        pressed = data.get('pressed', False)
        
        dpad_map = {
            'up': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            'down': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            'left': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            'right': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        }
        
        if direction in dpad_map:
            if pressed:
                self.gamepad.press_button(dpad_map[direction])
            else:
                self.gamepad.release_button(dpad_map[direction])
    
    def reset(self):
        """Reset gamepad to neutral state"""
        if self.active:
            self.gamepad.reset()
            self.gamepad.update()
    
    def __del__(self):
        """Cleanup"""
        if self.active:
            self.reset()