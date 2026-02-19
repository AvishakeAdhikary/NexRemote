import json
from datetime import datetime
from utils.paths import get_log_dir

class AuditLogger:
    """Security audit logger"""
    
    def __init__(self, config):
        self.log_file = get_log_dir() / 'audit.log'
    
    def log_event(self, event_type: str, data: dict):
        """Log security event"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')