import json
from datetime import datetime
from pathlib import Path

class AuditLogger:
    """Security audit logger"""
    
    def __init__(self, config):
        self.log_file = Path(config.get('data_dir')) / 'logs' / 'audit.log'
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event_type: str, data: dict):
        """Log security event"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')