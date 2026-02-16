import time

class InputValidator:
    """Validate input commands"""
    
    def __init__(self):
        self.valid_types = {
            'keyboard', 'mouse', 'gamepad', 'clipboard',
            'request_screen', 'file_transfer',
            'screen_share', 'media_control', 'task_manager',
            'camera', 'sensor', 'file_explorer'
        }
        
        self.rate_limits = {}
        self.max_rate = 1000  # messages per second
    
    def validate(self, data: dict) -> bool:
        """Validate input data"""
        msg_type = data.get('type')
        
        # Check type
        if msg_type not in self.valid_types:
            return False
        
        # Rate limiting
        client_id = data.get('client_id', 'unknown')
        current_time = time.time()
        
        if client_id not in self.rate_limits:
            self.rate_limits[client_id] = []
        
        # Clean old entries
        self.rate_limits[client_id] = [
            t for t in self.rate_limits[client_id]
            if current_time - t < 1.0
        ]
        
        # Check rate
        if len(self.rate_limits[client_id]) >= self.max_rate:
            return False
        
        self.rate_limits[client_id].append(current_time)
        
        # Type-specific validation
        if msg_type == 'keyboard':
            return self._validate_keyboard(data)
        elif msg_type == 'mouse':
            return self._validate_mouse(data)
        elif msg_type == 'gamepad':
            return self._validate_gamepad(data)
        
        return True
    
    def _validate_keyboard(self, data: dict) -> bool:
        """Validate keyboard input"""
        action = data.get('action')
        return action in {'type', 'press', 'release', 'hotkey'}
    
    def _validate_mouse(self, data: dict) -> bool:
        """Validate mouse input"""
        action = data.get('action')
        return action in {'move', 'move_relative', 'click', 'press', 'release', 'scroll'}
    
    def _validate_gamepad(self, data: dict) -> bool:
        """Validate gamepad input"""
        input_type = data.get('input_type')
        return input_type in {'button', 'trigger', 'joystick', 'dpad', 'gyro'}