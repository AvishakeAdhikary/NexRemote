"""
Virtual Camera
Receives video from Android and presents as webcam
Uses OBS Virtual Camera or similar
"""
import cv2
import numpy as np
import base64
from threading import Thread, Lock
from queue import Queue
from utils.logger import get_logger

logger = get_logger(__name__)

class VirtualCamera:
    """Virtual webcam implementation"""
    
    def __init__(self, config):
        self.config = config
        self.running = False
        
        # Frame buffer
        self.current_frame = None
        self.frame_lock = Lock()
        self.frame_queue = Queue(maxsize=5)
        
        # Virtual camera device index (usually set by OBS Virtual Camera)
        self.device_index = config.get('virtual_camera_index', 0)
        
        logger.info("Virtual camera initialized")
    
    def receive_frame(self, frame_base64: str):
        """Receive frame from Android device"""
        try:
            # Decode base64
            frame_bytes = base64.b64decode(frame_base64)
            
            # Convert to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            
            # Decode image
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                with self.frame_lock:
                    self.current_frame = frame
                
                # Add to queue for processing
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
            
        except Exception as e:
            logger.error(f"Error receiving frame: {e}")
    
    def get_current_frame(self) -> np.ndarray:
        """Get the current frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def start_virtual_camera(self):
        """
        Start virtual camera output
        
        Note: This requires OBS Virtual Camera or similar software to be installed.
        The actual implementation depends on the virtual camera driver being used.
        
        For OBS Virtual Camera:
        1. Install OBS Studio with Virtual Camera plugin
        2. Configure OBS to use a "Browser Source" or "Window Capture"
        3. Start Virtual Camera in OBS
        4. This code provides frames to be captured by OBS
        """
        try:
            self.running = True
            
            # Create a named window that OBS can capture
            cv2.namedWindow('Virtual Camera Feed', cv2.WINDOW_NORMAL)
            
            # Start display thread
            self.display_thread = Thread(target=self._display_loop, daemon=True)
            self.display_thread.start()
            
            logger.info("Virtual camera started (display window created)")
            
        except Exception as e:
            logger.error(f"Failed to start virtual camera: {e}")
    
    def _display_loop(self):
        """Display loop for virtual camera"""
        import time
        
        # Create a blank frame
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank_frame, 'Waiting for camera...', (150, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        while self.running:
            frame = self.get_current_frame()
            
            if frame is not None:
                cv2.imshow('Virtual Camera Feed', frame)
            else:
                cv2.imshow('Virtual Camera Feed', blank_frame)
            
            # Process events (required for cv2.imshow)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            time.sleep(0.033)  # ~30 FPS
    
    def stop_virtual_camera(self):
        """Stop virtual camera"""
        self.running = False
        
        if hasattr(self, 'display_thread'):
            self.display_thread.join(timeout=2)
        
        cv2.destroyAllWindows()
        logger.info("Virtual camera stopped")
    
    def save_snapshot(self, filename: str):
        """Save current frame as image"""
        frame = self.get_current_frame()
        if frame is not None:
            cv2.imwrite(filename, frame)
            logger.info(f"Snapshot saved to {filename}")
            return True
        return False
    
    def get_camera_info(self) -> dict:
        """Get virtual camera information"""
        frame = self.get_current_frame()
        
        if frame is not None:
            height, width = frame.shape[:2]
            return {
                'active': True,
                'width': width,
                'height': height,
                'fps': 30  # Approximate
            }
        else:
            return {
                'active': False,
                'width': 0,
                'height': 0,
                'fps': 0
            }
    
    def __del__(self):
        """Cleanup"""
        self.stop_virtual_camera()


class OBSVirtualCameraIntegration:
    """
    Helper class for OBS Virtual Camera integration
    
    This provides instructions and utilities for integrating with OBS
    """
    
    @staticmethod
    def get_setup_instructions() -> str:
        """Get setup instructions for OBS Virtual Camera"""
        return """
        OBS Virtual Camera Setup:
        
        1. Install OBS Studio: https://obsproject.com/
        
        2. In OBS, add a source:
           - Click '+' in Sources panel
           - Select 'Window Capture'
           - Choose 'Virtual Camera Feed' window
        
        3. Start Virtual Camera:
           - Click 'Start Virtual Camera' in OBS Controls
        
        4. The virtual camera will now be available in video conferencing apps
           as 'OBS Virtual Camera'
        
        Alternative: Use pyvirtualcam library for direct virtual camera support
        (requires platform-specific drivers)
        """
    
    @staticmethod
    def check_obs_installed() -> bool:
        """Check if OBS is installed"""
        import os
        import winreg
        
        try:
            # Check Windows registry for OBS
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\\OBS Studio")
            winreg.CloseKey(key)
            return True
        except:
            return False