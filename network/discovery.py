import socket
import threading
import json
import logging
from PyQt6.QtCore import pyqtSignal, QObject
logger_discovery = logging.getLogger(__name__)

class DiscoveryService(QObject):
    """UDP broadcast service for network discovery"""

    log_message = pyqtSignal(str)
    
    def __init__(self, server_port, discovery_port=8889):
        super().__init__()
        self.server_port = server_port
        self.discovery_port = discovery_port
        self.running = False
        self.socket = None
        self.thread = None
        
    def start(self):
        """Start discovery service"""
        if self.running:
            return
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.discovery_port))
        self.running = True
        
        self.thread = threading.Thread(target=self._listen)
        self.thread.start()
        
        logger_discovery.info(f"Discovery service started on port {self.discovery_port}")
    
    def _listen(self):
        """Listen for discovery requests"""
        while self.running:
            try:
                self.socket.settimeout(1.0)
                data, addr = self.socket.recvfrom(1024)
                
                message = json.loads(data.decode('utf-8'))
                if message.get('type') == 'discover':
                    self._respond(addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger_discovery.error(f"Discovery error: {e}")
    
    def _respond(self, addr):
        """Respond to discovery request"""
        try:
            # Get computer name
            import platform
            pc_name = platform.node()
            
            response = {
                'type': 'discover_response',
                'name': pc_name,
                'port': self.server_port,
                'version': '1.0'
            }
            
            response_data = json.dumps(response).encode('utf-8')
            self.socket.sendto(response_data, addr)
            
        except Exception as e:
            logger_discovery.error(f"Discovery response error: {e}")
    
    def stop(self):
        """Stop discovery service"""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=2)