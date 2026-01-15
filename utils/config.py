import json
import os
import logging

logger_config = logging.getLogger(__name__)

class Config:
    """Configuration management"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.data = self.load()
        
    def load(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger_config.error(f"Config load error: {e}")
        
        # Default configuration
        return {
            'server_port': 8888,
            'discovery_port': 8889,
            'screen_quality': 75,
            'mouse_sensitivity': 1.0,
            'enable_gamepad': True,
            'require_pairing': True,
            'auto_approve': False
        }
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger_config.error(f"Config save error: {e}")
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.data.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.data[key] = value