import json

class MessageHandler:
    """Handle protocol messages"""
    
    @staticmethod
    def create_message(msg_type: str, **kwargs) -> dict:
        """Create protocol message"""
        return {
            'type': msg_type,
            **kwargs
        }
    
    @staticmethod
    def parse_message(data: str) -> dict:
        """Parse protocol message"""
        return json.loads(data)