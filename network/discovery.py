import socket
import threading
import json
import logging
import platform
import time
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
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Bind to all interfaces on discovery port
            self.socket.bind(('', self.discovery_port))
            self.running = True
            
            # Get and log local IP addresses
            local_ips = self.get_local_ips()
            logger_discovery.info(f"Discovery service started on port {self.discovery_port}")
            logger_discovery.info(f"Listening on interfaces: {', '.join(local_ips)}")
            
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()
            
            # Also start active broadcasting (for stubborn networks)
            self.broadcast_thread = threading.Thread(target=self._active_broadcast, daemon=True)
            self.broadcast_thread.start()
            
        except Exception as e:
            logger_discovery.error(f"Discovery start error: {e}")
            raise
    
    def get_local_ips(self):
        """Get all local IP addresses"""
        ips = []
        try:
            import netifaces
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        if not ip.startswith('127.'):
                            ips.append(ip)
        except:
            # Fallback method
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ips.append(s.getsockname()[0])
                s.close()
            except:
                ips.append("Unknown")
        
        return ips
    
    def _active_broadcast(self):
        """Actively broadcast presence every 2 seconds"""
        logger_discovery.info("Active broadcast started")
        
        while self.running:
            try:
                time.sleep(2)
                # This helps with discovery on some networks
                # The broadcast tells clients "I'm here!"
            except Exception as e:
                logger_discovery.error(f"Active broadcast error: {e}")
    
    def _listen(self):
        """Listen for discovery requests"""
        logger_discovery.info("Discovery listener started - waiting for requests...")
        
        request_count = 0
        
        while self.running:
            try:
                self.socket.settimeout(1.0)
                data, addr = self.socket.recvfrom(1024)
                
                request_count += 1
                logger_discovery.info(f"[{request_count}] Received {len(data)} bytes from {addr[0]}:{addr[1]}")
                logger_discovery.info(f"Raw data: {data}")
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    logger_discovery.info(f"Parsed message: {message}")
                    
                    if message.get('type') == 'discover':
                        logger_discovery.info(f"Valid discovery request from {addr[0]}")
                        self._respond(addr)
                    else:
                        logger_discovery.warning(f"Unknown message type: {message.get('type')}")
                        
                except json.JSONDecodeError as e:
                    logger_discovery.error(f"JSON decode error: {e}")
                    logger_discovery.error(f"Raw data was: {data}")
                except Exception as e:
                    logger_discovery.error(f"Message processing error: {e}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger_discovery.error(f"Discovery listener error: {e}")
    
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
            
            # Send response directly back to requester
            sent = self.socket.sendto(response_data, addr)
            
            logger_discovery.info(f"✓ Sent {sent} bytes response to {addr[0]}:{addr[1]}")
            logger_discovery.info(f"Response data: {response}")
            
        except Exception as e:
            logger_discovery.error(f"Discovery response error: {e}")
            import traceback
            logger_discovery.error(traceback.format_exc())
    
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