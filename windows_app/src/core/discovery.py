"""
UDP Discovery Service
Allows clients to find the server on local network
"""
import asyncio
import socket
import json
from utils.logger import get_logger

logger = get_logger(__name__)

class DiscoveryService:
    """UDP broadcast service for device discovery"""
    
    DISCOVERY_PORT = 37020
    MAGIC_BYTES = b'NEXREMOTE_DISCOVER'
    
    def __init__(self, config):
        self.config = config
        self.running = False
        self.socket = None
        
    async def start(self, response_callback):
        """Start listening for discovery requests"""
        try:
            self.running = True
            
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', self.DISCOVERY_PORT))
            
            logger.info(f"Discovery service listening on port {self.DISCOVERY_PORT}")
            
            while self.running:
                try:
                    # Receive discovery request
                    data, addr = await asyncio.get_event_loop().run_in_executor(
                        None, self.socket.recvfrom, 1024
                    )
                    
                    if data.startswith(self.MAGIC_BYTES):
                        logger.info(f"Discovery request from {addr}")
                        
                        # Get response from callback
                        response = response_callback(addr)
                        
                        # Send response
                        response_data = json.dumps(response).encode('utf-8')
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.socket.sendto, response_data, addr
                        )
                        
                        logger.debug(f"Sent discovery response to {addr}")
                        
                except Exception as e:
                    if self.running:
                        logger.error(f"Error handling discovery request: {e}")
                    
        except Exception as e:
            logger.error(f"Discovery service error: {e}", exc_info=True)
        finally:
            if self.socket:
                self.socket.close()
    
    def stop(self):
        """Stop the discovery service"""
        self.running = False
        logger.info("Discovery service stopped")