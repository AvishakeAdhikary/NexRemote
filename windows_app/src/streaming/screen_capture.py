"""
Screen Capture
Captures and encodes screen for streaming
"""
import mss
import cv2
import numpy as np
import base64
from threading import Thread, Lock
from queue import Queue
from utils.logger import get_logger

logger = get_logger(__name__)

class ScreenCapture:
    """Screen capture and encoding"""
    
    def __init__(self, config):
        self.config = config
        self.running = False
        
        # Settings
        self.fps = config.get('screen_fps', 30)
        self.quality = config.get('screen_quality', 50)  # 1-100
        self.scale = config.get('screen_scale', 0.5)  # Scale factor
        
        # Frame queue
        self.frame_queue = Queue(maxsize=2)
        self.lock = Lock()
        
        # Get monitor info using a temporary mss instance
        with mss.mss() as sct:
            self.monitors_info = sct.monitors
            self.monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        
        logger.info(f"Screen capture initialized: {self.monitor['width']}x{self.monitor['height']} @ {self.fps}fps")
    
    def capture_frame(self) -> str:
        """Capture a single frame and return as base64 encoded JPEG.
        Creates a new mss instance each time to avoid thread-local storage issues."""
        try:
            with mss.mss() as sct:
                # Capture screenshot
                screenshot = sct.grab(self.monitor)
                
                # Convert to numpy array
                frame = np.array(screenshot)
            
            # Convert BGRA to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Scale if needed
            if self.scale != 1.0:
                width = int(frame.shape[1] * self.scale)
                height = int(frame.shape[0] * self.scale)
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            
            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert to base64
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return frame_base64
            
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return ""
    
    def start_streaming(self, callback):
        """Start continuous screen streaming"""
        self.running = True
        self.stream_thread = Thread(target=self._streaming_loop, args=(callback,), daemon=True)
        self.stream_thread.start()
        logger.info("Screen streaming started")
    
    def _streaming_loop(self, callback):
        """Streaming loop running in separate thread"""
        import time
        frame_time = 1.0 / self.fps
        
        while self.running:
            start_time = time.time()
            
            # Capture and encode frame
            frame_data = self.capture_frame()
            
            if frame_data:
                # Call callback with frame data
                callback(frame_data)
            
            # Maintain FPS
            elapsed = time.time() - start_time
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def stop_streaming(self):
        """Stop screen streaming"""
        self.running = False
        if hasattr(self, 'stream_thread'):
            self.stream_thread.join(timeout=2)
        logger.info("Screen streaming stopped")
    
    def get_monitors(self) -> list:
        """Get list of available monitors"""
        monitors = []
        try:
            with mss.mss() as sct:
                for i, monitor in enumerate(sct.monitors[1:], 1):  # Skip "all monitors"
                    monitors.append({
                        'id': i,
                        'width': monitor['width'],
                        'height': monitor['height'],
                        'left': monitor['left'],
                        'top': monitor['top']
                    })
        except Exception as e:
            logger.error(f"Error getting monitors: {e}")
        return monitors
    
    def set_monitor(self, monitor_id: int):
        """Set which monitor to capture"""
        try:
            with mss.mss() as sct:
                if 0 < monitor_id < len(sct.monitors):
                    self.monitor = sct.monitors[monitor_id]
                    logger.info(f"Monitor changed to #{monitor_id}")
                else:
                    logger.warning(f"Invalid monitor ID: {monitor_id}")
        except Exception as e:
            logger.error(f"Error setting monitor: {e}")
    
    def set_quality(self, quality: int):
        """Set JPEG quality (1-100)"""
        self.quality = max(1, min(100, quality))
        logger.info(f"Quality set to {self.quality}")
    
    def set_fps(self, fps: int):
        """Set capture FPS"""
        self.fps = max(1, min(60, fps))
        logger.info(f"FPS set to {self.fps}")
    
    def set_scale(self, scale: float):
        """Set scale factor (0.1-1.0)"""
        self.scale = max(0.1, min(1.0, scale))
        logger.info(f"Scale set to {self.scale}")
    
    def __del__(self):
        """Cleanup"""
        self.stop_streaming()