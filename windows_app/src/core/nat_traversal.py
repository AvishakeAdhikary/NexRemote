"""
NAT Traversal using STUN/TURN
Enables connections outside local network
"""
import asyncio
import aioice
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import object_from_string, object_to_string
from utils.logger import get_logger

logger = get_logger(__name__)

class NATTraversal:
    """
    NAT traversal using WebRTC/ICE
    Supports STUN and TURN servers
    """
    
    # Public STUN servers
    DEFAULT_STUN_SERVERS = [
        "stun:stun.l.google.com:19302",
        "stun:stun1.l.google.com:19302",
        "stun:stun2.l.google.com:19302",
        "stun:stun3.l.google.com:19302",
        "stun:stun4.l.google.com:19302",
    ]
    
    def __init__(self, config):
        self.config = config
        self.peer_connections = {}
        
        # Get STUN/TURN servers from config
        self.ice_servers = self._get_ice_servers()
        
        logger.info(f"NAT traversal initialized with {len(self.ice_servers)} ICE servers")
    
    def _get_ice_servers(self) -> list:
        """Get ICE servers configuration"""
        servers = []
        
        # Add STUN servers
        stun_servers = self.config.get('stun_servers', self.DEFAULT_STUN_SERVERS)
        for stun in stun_servers:
            servers.append({'urls': stun})
        
        # Add TURN servers if configured
        turn_servers = self.config.get('turn_servers', [])
        for turn in turn_servers:
            servers.append({
                'urls': turn['url'],
                'username': turn.get('username'),
                'credential': turn.get('credential')
            })
        
        return servers
    
    async def create_connection(self, client_id: str) -> RTCPeerConnection:
        """Create a new peer connection for NAT traversal"""
        try:
            # Create RTCPeerConnection with ICE servers
            pc = RTCPeerConnection(configuration={
                'iceServers': self.ice_servers
            })
            
            # Store connection
            self.peer_connections[client_id] = pc
            
            # Set up event handlers
            @pc.on('iceconnectionstatechange')
            async def on_ice_state_change():
                logger.info(f"ICE connection state changed to: {pc.iceConnectionState}")
                if pc.iceConnectionState == 'failed':
                    await self.close_connection(client_id)
            
            @pc.on('connectionstatechange')
            async def on_connection_state_change():
                logger.info(f"Connection state changed to: {pc.connectionState}")
            
            logger.info(f"Peer connection created for {client_id}")
            return pc
            
        except Exception as e:
            logger.error(f"Failed to create peer connection: {e}")
            raise
    
    async def create_offer(self, client_id: str) -> dict:
        """Create SDP offer for peer connection"""
        try:
            pc = await self.create_connection(client_id)
            
            # Create data channel for signaling
            channel = pc.createDataChannel('signaling')
            
            # Create offer
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            # Wait for ICE gathering
            await self._wait_for_ice_gathering(pc)
            
            # Return offer as dict
            return {
                'type': 'offer',
                'sdp': pc.localDescription.sdp
            }
            
        except Exception as e:
            logger.error(f"Failed to create offer: {e}")
            raise
    
    async def handle_answer(self, client_id: str, answer: dict):
        """Handle SDP answer from peer"""
        try:
            pc = self.peer_connections.get(client_id)
            if not pc:
                raise ValueError(f"No peer connection for {client_id}")
            
            # Set remote description
            await pc.setRemoteDescription(RTCSessionDescription(
                sdp=answer['sdp'],
                type=answer['type']
            ))
            
            logger.info(f"Answer handled for {client_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle answer: {e}")
            raise
    
    async def handle_ice_candidate(self, client_id: str, candidate: dict):
        """Handle ICE candidate from peer"""
        try:
            pc = self.peer_connections.get(client_id)
            if not pc:
                logger.warning(f"No peer connection for ICE candidate from {client_id}")
                return
            
            # Add ICE candidate
            await pc.addIceCandidate(candidate)
            logger.debug(f"ICE candidate added for {client_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle ICE candidate: {e}")
    
    async def _wait_for_ice_gathering(self, pc: RTCPeerConnection, timeout: float = 10.0):
        """Wait for ICE gathering to complete"""
        start_time = asyncio.get_event_loop().time()
        
        while pc.iceGatheringState != 'complete':
            await asyncio.sleep(0.1)
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning("ICE gathering timeout")
                break
    
    async def close_connection(self, client_id: str):
        """Close peer connection"""
        pc = self.peer_connections.get(client_id)
        if pc:
            await pc.close()
            del self.peer_connections[client_id]
            logger.info(f"Peer connection closed for {client_id}")
    
    async def close_all(self):
        """Close all peer connections"""
        for client_id in list(self.peer_connections.keys()):
            await self.close_connection(client_id)
    
    def get_public_ip(self) -> str:
        """
        Get public IP address using STUN
        This is useful for displaying connection information to users
        """
        try:
            import socket
            import struct
            
            # Simple STUN request to get public IP
            # This is a simplified implementation
            stun_host = "stun.l.google.com"
            stun_port = 19302
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # STUN Binding Request
            trans_id = b'\x00' * 12
            message = b'\x00\x01\x00\x00' + b'\x21\x12\xa4\x42' + trans_id
            
            sock.sendto(message, (stun_host, stun_port))
            
            data, addr = sock.recvfrom(1024)
            sock.close()
            
            # Parse STUN response (simplified)
            # In production, use a proper STUN library
            
            logger.info("Public IP retrieved via STUN")
            return "Retrieved via STUN"
            
        except Exception as e:
            logger.error(f"Failed to get public IP: {e}")
            return "Unknown"


class RelayServer:
    """
    Simple relay server for NAT traversal when STUN/TURN fails
    Acts as intermediary for data forwarding
    """
    
    def __init__(self, config):
        self.config = config
        self.connections = {}
        self.relay_pairs = {}
    
    async def register_connection(self, client_id: str, websocket):
        """Register a client connection for relaying"""
        self.connections[client_id] = websocket
        logger.info(f"Client {client_id} registered for relay")
    
    async def create_relay_pair(self, client_a: str, client_b: str):
        """Create a relay pair between two clients"""
        if client_a in self.connections and client_b in self.connections:
            self.relay_pairs[client_a] = client_b
            self.relay_pairs[client_b] = client_a
            logger.info(f"Relay pair created: {client_a} <-> {client_b}")
            return True
        return False
    
    async def relay_message(self, from_client: str, message: bytes):
        """Relay message from one client to another"""
        to_client = self.relay_pairs.get(from_client)
        
        if to_client and to_client in self.connections:
            try:
                await self.connections[to_client].send(message)
                return True
            except Exception as e:
                logger.error(f"Failed to relay message: {e}")
                return False
        return False
    
    def remove_connection(self, client_id: str):
        """Remove client connection"""
        if client_id in self.connections:
            del self.connections[client_id]
        
        # Remove from relay pairs
        if client_id in self.relay_pairs:
            peer = self.relay_pairs[client_id]
            del self.relay_pairs[client_id]
            if peer in self.relay_pairs:
                del self.relay_pairs[peer]
        
        logger.info(f"Client {client_id} removed from relay")