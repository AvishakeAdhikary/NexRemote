import hashlib
import json
import time
from typing import Dict
from utils.paths import get_data_dir

class DeviceAuthenticator:
    """Device authentication manager"""
    
    def __init__(self, config):
        self.config = config
        self.trusted_devices: Dict[str, dict] = self._load_trusted_devices()
    
    def _load_trusted_devices(self) -> Dict[str, dict]:
        """Load trusted devices from storage"""
        devices_file = get_data_dir() / 'trusted_devices.json'
        if devices_file.exists():
            with open(devices_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_trusted_devices(self):
        """Save trusted devices"""
        devices_file = get_data_dir() / 'trusted_devices.json'
        devices_file.parent.mkdir(parents=True, exist_ok=True)
        with open(devices_file, 'w') as f:
            json.dump(self.trusted_devices, f, indent=2)
    
    async def validate(self, auth_data: dict) -> bool:
        """Validate authentication request"""
        device_id = auth_data.get('device_id')
        device_name = auth_data.get('device_name')
        
        if not device_id or not device_name:
            return False
        
        # Check if device is trusted
        if device_id in self.trusted_devices:
            device_info = self.trusted_devices[device_id]
            device_info['last_connected'] = time.time()
            self._save_trusted_devices()
            return True
        
        # New device - allow through, will need approval in next step
        return True
    
    def add_trusted_device(self, device_id: str, device_name: str):
        """Add device to trusted list"""
        self.trusted_devices[device_id] = {
            'name': device_name,
            'first_connected': time.time(),
            'last_connected': time.time(),
        }
        self._save_trusted_devices()
    
    def remove_trusted_device(self, device_id: str):
        """Remove device from trusted list"""
        if device_id in self.trusted_devices:
            del self.trusted_devices[device_id]
            self._save_trusted_devices()