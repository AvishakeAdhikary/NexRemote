import mss
import cv2
import base64
import numpy as np
import logging

logger_screen = logging.getLogger(__name__)

class ScreenCapture:
    """Screen capture and encoding"""
    
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]  # Primary monitor
        
    def capture_frame(self, quality=75):
        """Capture and encode screen frame"""
        try:
            # Capture screenshot
            screenshot = self.sct.grab(self.monitor)
            
            # Convert to numpy array
            frame = np.array(screenshot)
            
            # Convert BGRA to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Resize for performance (optional)
            height, width = frame.shape[:2]
            if width > 1280:
                scale = 1280 / width
                new_width = 1280
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert to base64
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return frame_base64
        except Exception as e:
            logger_screen.error(f"Screen capture error: {e}")
            return None