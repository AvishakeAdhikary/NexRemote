import json
from pathlib import Path
import uuid
import socket

class Config:
    """Configuration management"""
    
    def __init__(self, config_file: str = './data/config.json'):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return self._create_default_config()
    
    def _create_default_config(self) -> dict:
        """Create default configuration"""
        config = {
            'pc_name': socket.gethostname(),
            'device_id': str(uuid.uuid4()),
            'server_port': 8765,
            'server_port_insecure': 8766,
            'discovery_port': 37020,
            'enable_remote_access': False,
            'max_clients': 5,
            'data_dir': './data',
            'log_level': 'INFO',
            'auto_start': False,
            'minimize_to_tray': True,
            'require_approval': True,
        }
        self.save(config)
        return config
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value"""
        self.config[key] = value
    
    def save(self, config: dict = None):
        """Save configuration to file"""
        if config:
            self.config = config
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)