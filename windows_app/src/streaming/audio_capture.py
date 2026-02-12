"""
Audio Capture
Captures system audio for streaming
"""
import pyaudio
import wave
import numpy as np
import base64
from threading import Thread
from queue import Queue
from utils.logger import get_logger

logger = get_logger(__name__)

class AudioCapture:
    """System audio capture"""
    
    def __init__(self, config):
        self.config = config
        self.running = False
        
        # Audio settings
        self.sample_rate = config.get('audio_sample_rate', 44100)
        self.channels = config.get('audio_channels', 2)
        self.chunk_size = config.get('audio_chunk_size', 1024)
        
        # PyAudio
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = None
            logger.info(f"Audio capture initialized: {self.sample_rate}Hz, {self.channels} channels")
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            self.audio = None
    
    def list_devices(self) -> list:
        """List available audio devices"""
        if not self.audio:
            return []
        
        devices = []
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:  # Input device
                    devices.append({
                        'id': i,
                        'name': info['name'],
                        'channels': info['maxInputChannels'],
                        'sample_rate': int(info['defaultSampleRate'])
                    })
            except Exception as e:
                logger.warning(f"Error getting device info for index {i}: {e}")
        
        return devices
    
    def start_capture(self, callback, device_index=None):
        """Start audio capture"""
        if not self.audio:
            logger.error("Audio not initialized")
            return False
        
        try:
            # Open audio stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=lambda in_data, frame_count, time_info, status: 
                    self._audio_callback(in_data, callback)
            )
            
            self.running = True
            self.stream.start_stream()
            logger.info("Audio capture started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            return False
    
    def _audio_callback(self, in_data, user_callback):
        """Audio stream callback"""
        if self.running:
            # Encode audio data
            audio_base64 = base64.b64encode(in_data).decode('utf-8')
            
            # Call user callback
            user_callback({
                'data': audio_base64,
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'format': 'pcm_s16le'
            })
        
        return (in_data, pyaudio.paContinue)
    
    def stop_capture(self):
        """Stop audio capture"""
        self.running = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                logger.info("Audio capture stopped")
            except Exception as e:
                logger.error(f"Error stopping audio: {e}")
    
    def get_volume_level(self) -> float:
        """Get current audio volume level (0.0-1.0)"""
        if not self.stream or not self.stream.is_active():
            return 0.0
        
        try:
            # Read audio chunk
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            
            # Convert to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Calculate RMS (root mean square) volume
            rms = np.sqrt(np.mean(audio_data**2))
            
            # Normalize to 0-1 range (assuming max value is 32767 for int16)
            volume = min(1.0, rms / 32767.0)
            
            return volume
        except Exception as e:
            logger.error(f"Error getting volume level: {e}")
            return 0.0
    
    def __del__(self):
        """Cleanup"""
        self.stop_capture()
        if self.audio:
            self.audio.terminate()