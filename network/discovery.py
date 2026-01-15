import socket
import threading
import json
import logging
from PyQt6.QtCore import pyqtSignal, QObject
logger_discovery = logging.getLogger(__name__)

class DiscoveryService:
    """UDP broadcast service for network discovery"""
    
    def __init__(self, server_port, discovery_port=8889):
        self.server_port = server_port
        self.discovery_port = discovery_port
        self.running = False
        self.socket = None
        self.thread = None
        
    def start(self):
        """Start discovery service"""
        if self.running:
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.bind(('', self.discovery_port))
            self.running = True
            
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()
            
            logger_discovery.info(f"Discovery service started on port {self.discovery_port}")
            
        except Exception as e:
            logger_discovery.error(f"Discovery start error: {e}")
            raise
    
    def _listen(self):
        """Listen for discovery requests"""
        logger_discovery.info("Discovery service listening for broadcasts...")
        
        while self.running:
            try:
                self.socket.settimeout(1.0)
                data, addr = self.socket.recvfrom(1024)
                
                logger_discovery.info(f"Received discovery request from {addr}")
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    if message.get('type') == 'discover':
                        logger_discovery.info(f"Valid discovery request, responding to {addr}")
                        self._respond(addr)
                except json.JSONDecodeError:
                    logger_discovery.warning(f"Invalid JSON from {addr}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger_discovery.error(f"Discovery error: {e}")
    
    def _respond(self, addr):
        """Respond to discovery request"""
        try:
            pc_name = platform.node()
            
            response = {
                'type': 'discover_response',
                'name': pc_name,
                'port': self.server_port,
                'version': '2.0',
                'requires_pairing': True
            }
            
            response_data = json.dumps(response).encode('utf-8')
            self.socket.sendto(response_data, addr)
            
            logger_discovery.info(f"Sent discovery response to {addr}: {pc_name}")
            
        except Exception as e:
            logger_discovery.error(f"Discovery response error: {e}")
    
    def stop(self):
        """Stop discovery service"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=2)
        logger_discovery.info("Discovery service stopped")