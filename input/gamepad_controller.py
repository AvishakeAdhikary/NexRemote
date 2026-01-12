"""
Virtual Xbox Gamepad Controller
"""
import logging
import vgamepad as vg

logger = logging.getLogger(__name__)

class GamepadController:
    """Controls virtual Xbox gamepad"""
    
    def __init__(self):
        try:
            self.gamepad = vg.VX360Gamepad()
            self.connected = True
            logger.info("Virtual gamepad initialized")
        except Exception as e:
            logger.error(f"Failed to initialize virtual gamepad: {e}")
            self.gamepad = None
            self.connected = False
        
        # Button mapping
        self.button_map = {
            'a': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            'b': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            'x': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            'y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            'lb': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            'rb': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            'back': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            'start': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            'l3': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            'r3': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
            'up': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            'down': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            'left': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            'right': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        }
    
    def button(self, button_name, pressed):
        """Press or release button"""
        if not self.connected:
            return
            
        try:
            button_name = button_name.lower()
            if button_name in self.button_map:
                button_obj = self.button_map[button_name]
                if pressed:
                    self.gamepad.press_button(button=button_obj)
                else:
                    self.gamepad.release_button(button=button_obj)
                self.gamepad.update()
        except Exception as e:
            logger.error(f"Gamepad button error: {e}")
    
    def axis(self, axis_name, value):
        """Set analog stick axis value (-1.0 to 1.0)"""
        if not self.connected:
            return
            
        try:
            axis_name = axis_name.lower()
            # Convert -1.0 to 1.0 range to -32768 to 32767
            int_value = int(value * 32767)
            
            if axis_name == 'left_x':
                self.gamepad.left_joystick(x_value=int_value, y_value=self.gamepad.left_joystick_float[1])
            elif axis_name == 'left_y':
                self.gamepad.left_joystick(x_value=self.gamepad.left_joystick_float[0], y_value=int_value)
            elif axis_name == 'right_x':
                self.gamepad.right_joystick(x_value=int_value, y_value=self.gamepad.right_joystick_float[1])
            elif axis_name == 'right_y':
                self.gamepad.right_joystick(x_value=self.gamepad.right_joystick_float[0], y_value=int_value)
            
            self.gamepad.update()
        except Exception as e:
            logger.error(f"Gamepad axis error: {e}")
    
    def trigger(self, trigger_name, value):
        """Set trigger value (0.0 to 1.0)"""
        if not self.connected:
            return
            
        try:
            trigger_name = trigger_name.lower()
            # Convert 0.0 to 1.0 range to 0 to 255
            int_value = int(value * 255)
            
            if trigger_name == 'lt' or trigger_name == 'l2':
                self.gamepad.left_trigger(value=int_value)
            elif trigger_name == 'rt' or trigger_name == 'r2':
                self.gamepad.right_trigger(value=int_value)
            
            self.gamepad.update()
        except Exception as e:
            logger.error(f"Gamepad trigger error: {e}")
    
    def reset(self):
        """Reset gamepad to neutral state"""
        if not self.connected:
            return
            
        try:
            self.gamepad.reset()
            self.gamepad.update()
        except Exception as e:
            logger.error(f"Gamepad reset error: {e}")