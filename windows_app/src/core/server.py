"""
WebSocket Server with TLS support
Handles multiple client connections
"""
import asyncio
import websockets
import ssl
import json
from typing import Set, Dict
from PyQt6.QtCore import QObject, pyqtSignal
from core.discovery import DiscoveryService
from core.connection_manager import ConnectionManager
from core.certificate_manager import CertificateManager
from security.encryption import MessageEncryption
from security.authentication import DeviceAuthenticator
from security.audit_logger import AuditLogger
from input.virtual_keyboard import VirtualKeyboard
from input.virtual_mouse import VirtualMouse
from input.virtual_gamepad import VirtualGamepad
from input.media_controller import MediaController
from input.input_validator import InputValidator
from streaming.screen_capture import ScreenCapture
from streaming.virtual_camera import VirtualCamera
from ui.file_explorer import FileExplorer
from ui.task_manager import TaskManager
from utils.logger import get_logger
from utils.protocol import MessageHandler

logger = get_logger(__name__)

class NexRemoteServer(QObject):
    """Main server handling all client connections"""
    
    # Signals for UI updates
    client_connected = pyqtSignal(str, str)  # client_id, device_name
    client_disconnected = pyqtSignal(str)
    message_received = pyqtSignal(str, dict)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = False
        
        # Initialize components
        self.cert_manager = CertificateManager(config)
        self.discovery = DiscoveryService(config)
        self.connection_manager = ConnectionManager(config)
        self.authenticator = DeviceAuthenticator(config)
        self.encryption = MessageEncryption()
        self.audit_logger = AuditLogger(config)
        self.message_handler = MessageHandler()
        self.input_validator = InputValidator()
        
        # Input handlers
        self.keyboard = VirtualKeyboard()
        self.mouse = VirtualMouse()
        self.gamepad = VirtualGamepad()
        self.media_controller = MediaController()
        
        # Streaming and camera
        self.screen_capture = ScreenCapture(config)
        self.virtual_camera = VirtualCamera(config)
        
        # File system and process management
        self.file_explorer = FileExplorer(config)
        self.task_manager = TaskManager()
        
        # Active connections
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        logger.info("Server initialized")
    
    async def start(self):
        """Start the server(s)"""
        try:
            self.running = True
            
            # Start discovery service
            asyncio.create_task(self.discovery.start(self._on_discovery_request))
            
            # Start both secure and non-secure servers
            secure_task = asyncio.create_task(self.start_secure_server())
            insecure_task = asyncio.create_task(self.start_non_secure_server())
            
            await asyncio.gather(secure_task, insecure_task)
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            self.running = False
    
    async def start_secure_server(self):
        """Start secure WebSocket server (WSS)"""
        try:
            # Generate or load SSL certificate
            ssl_context = self.cert_manager.get_ssl_context()
            
            port = self.config.get('server_port', 8765)
            
            async with websockets.serve(
                self.handle_client,
                "0.0.0.0",
                port,
                ssl=ssl_context,
                max_size=10 * 1024 * 1024,  # 10MB max message size
                ping_interval=20,
                ping_timeout=10
            ):
                logger.info(f"Secure server (WSS) listening on port {port}")
                await asyncio.Future()  # Run forever
        except Exception as e:
            logger.error(f"Secure server error: {e}", exc_info=True)
    
    async def start_non_secure_server(self):
        """Start non-secure WebSocket server (WS) for local development"""
        try:
            port = self.config.get('server_port_insecure', 8766)
            
            async with websockets.serve(
                self.handle_client,
                "0.0.0.0",
                port,
                ssl=None,  # No SSL for local development
                max_size=10 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=10
            ):
                logger.info(f"Non-secure server (WS) listening on port {port}")
                await asyncio.Future()  # Run forever
        except Exception as e:
            logger.error(f"Non-secure server error: {e}", exc_info=True)
    
    async def handle_client(self, websocket, path=None):
        """Handle individual client connection"""
        client_id = None
        device_name = "Unknown"
        
        try:
            # Wait for authentication message
            auth_msg = await asyncio.wait_for(websocket.recv(), timeout=30)
            
            # Try to parse as plain JSON first (for auth)
            try:
                auth_data = json.loads(auth_msg)
                logger.info(f"Received plain JSON auth from {websocket.remote_address}")
            except (json.JSONDecodeError, TypeError):
                # If it fails, try to decrypt (backward compatibility)
                logger.info(f"Auth message encrypted, attempting to decrypt from {websocket.remote_address}")
                decrypted = self.encryption.decrypt(auth_msg)
                auth_data = json.loads(decrypted)
            
            # Validate authentication
            if not await self.authenticator.validate(auth_data):
                await websocket.send(json.dumps({"type": "auth_failed"}))
                logger.warning(f"Authentication failed from {websocket.remote_address}")
                self.audit_logger.log_event("auth_failed", {"address": str(websocket.remote_address)})
                return
            
            client_id = auth_data.get('device_id')
            device_name = auth_data.get('device_name', 'Unknown')
            
            # Check if connection should be approved
            if not await self.connection_manager.request_approval(client_id, device_name):
                await websocket.send(json.dumps({"type": "connection_rejected"}))
                logger.info(f"Connection rejected: {device_name}")
                return
            
            # Register client
            self.clients[client_id] = websocket
            self.client_connected.emit(client_id, device_name)
            self.audit_logger.log_event("client_connected", {"client_id": client_id, "device_name": device_name})
            
            # Send success response
            await websocket.send(json.dumps({
                "type": "auth_success",
                "server_name": self.config.get('pc_name', 'PC'),
                "capabilities": self.get_capabilities()
            }))
            
            logger.info(f"Client connected: {device_name} ({client_id})")
            
            # Handle messages
            async for message in websocket:
                await self.process_message(client_id, message)
                
        except asyncio.TimeoutError:
            logger.warning("Client authentication timeout")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {device_name}")
        except Exception as e:
            logger.error(f"Error handling client: {e}", exc_info=True)
        finally:
            # Cleanup
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                self.client_disconnected.emit(client_id)
                self.audit_logger.log_event("client_disconnected", {"client_id": client_id})
    
    async def process_message(self, client_id: str, message: bytes):
        """Process incoming message from client"""
        msg_type = 'unknown'  # Initialize for error handling
        try:
            # Decrypt message
            decrypted = self.encryption.decrypt(message)
            
            # Debug: Log the decrypted data
            logger.info(f"Decrypted data length: {len(decrypted)}")
            logger.info(f"Decrypted data (first 200 chars): {decrypted[:200]}")
            logger.info(f"Decrypted data repr: {repr(decrypted[:200])}")
            
            data = json.loads(decrypted)
            
            msg_type = data.get('type', 'unknown')
            logger.info(f"Received message type: {msg_type} from {client_id}")
            
            # Validate input
            if not self.input_validator.validate(data):
                logger.warning(f"Invalid message from {client_id}: {msg_type}")
                self.audit_logger.log_event("invalid_message", {"client_id": client_id, "type": msg_type})
                return
            
            # Route to appropriate handler
            if msg_type == 'keyboard':
                self.keyboard.send_key(data)
            elif msg_type == 'mouse':
                self.mouse.send_input(data)
            elif msg_type == 'gamepad':
                self.gamepad.send_input(data)
            elif msg_type == 'camera':
                self._handle_camera(data)
            elif msg_type == 'file_explorer':
                response = self.file_explorer.handle_request(data)
                await self._send_response(client_id, response)
            elif msg_type == 'screen_share':
                await self._handle_screen_share(client_id, data)
            elif msg_type == 'media_control':
                self.media_controller.send_command(data)
            elif msg_type == 'task_manager':
                response = self.task_manager.handle_request(data)
                await self._send_response(client_id, response)
            elif msg_type == 'request_screen':
                await self.send_screen_frame(client_id)
            elif msg_type == 'clipboard':
                self.handle_clipboard(data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
            
            # Emit signal (may fail if no UI connected)
            try:
                self.message_received.emit(client_id, data)
            except Exception as emit_error:
                logger.debug(f"Signal emit warning (non-critical): {emit_error}")
            
        except AttributeError as e:
            logger.error(f"Handler attribute error for message type '{msg_type}': {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error processing message type '{msg_type}': {type(e).__name__}: {e}", exc_info=True)
    
    async def send_screen_frame(self, client_id: str):
        """Send screen frame to client"""
        try:
            if client_id not in self.clients:
                return
            
            frame = self.screen_capture.capture_frame()
            
            message = json.dumps({
                "type": "screen_frame",
                "data": frame
            })
            
            encrypted = self.encryption.encrypt(message)
            await self.clients[client_id].send(encrypted)
            
        except Exception as e:
            logger.error(f"Error sending screen frame: {e}")
    
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """Broadcast message to all connected clients"""
        exclude = exclude or set()
        encrypted = self.encryption.encrypt(json.dumps(message))
        
        disconnected = []
        for client_id, ws in self.clients.items():
            if client_id not in exclude:
                try:
                    await ws.send(encrypted)
                except:
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]
    
    def get_capabilities(self) -> dict:
        """Return server capabilities"""
        return {
            "keyboard": True,
            "mouse": True,
            "gamepad": True,
            "screen_streaming": True,
            "virtual_camera": True,
            "file_transfer": True,
            "clipboard": True,
            "multi_display": True
        }
    
    def _on_discovery_request(self, addr):
        """Handle discovery request"""
        return {
            "type": "discovery_response",
            "name": self.config.get('pc_name', 'PC'),
            "port": self.config.get('server_port', 8765),
            "port_insecure": self.config.get('server_port_insecure', 8766),
            "id": self.config.get('device_id'),
            "version": "1.0.0"
        }
    
    def stop(self):
        """Stop the server"""
        self.running = False
        self.discovery.stop()
        logger.info("Server stopped")
    
    def handle_clipboard(self, data):
        """Handle clipboard sync"""
        # Implementation for clipboard handling
        pass
    
    def _handle_camera(self, data: dict):
        """Handle camera-related messages"""
        try:
            action = data.get('action')
            
            if action == 'start':
                self.virtual_camera.start_virtual_camera()
                logger.info("Virtual camera started")
            elif action == 'stop':
                self.virtual_camera.stop_virtual_camera()
                logger.info("Virtual camera stopped")
            elif action == 'frame':
                frame_data = data.get('data')
                if frame_data:
                    self.virtual_camera.receive_frame(frame_data)
        except Exception as e:
            logger.error(f"Error handling camera: {e}", exc_info=True)
    
    async def _handle_screen_share(self, client_id: str, data: dict):
        """Handle screen share requests"""
        try:
            action = data.get('action')
            
            if action == 'start':
                logger.info(f"Screen sharing started for client {client_id}")
            elif action == 'stop':
                logger.info(f"Screen sharing stopped for client {client_id}")
            elif action == 'request_frame':
                display_index = data.get('display_index', 0)
                await self.send_screen_frame(client_id)
            elif action == 'list_displays':
                # Return list of available displays (placeholder for now)
                response = {
                    'action': 'display_list',
                    'displays': [
                        {'index': 0, 'name': 'Primary Display', 'width': 1920, 'height': 1080}
                    ]
                }
                await self._send_response(client_id, response)
        except Exception as e:
            logger.error(f"Error handling screen share: {e}", exc_info=True)
    
    async def _send_response(self, client_id: str, response: dict):
        """Send a response message to a specific client"""
        try:
            if client_id not in self.clients:
                logger.warning(f"Cannot send response to disconnected client {client_id}")
                return
            
            message = json.dumps(response)
            encrypted = self.encryption.encrypt(message)
            await self.clients[client_id].send(encrypted)
            
        except Exception as e:
            logger.error(f"Error sending response to {client_id}: {e}", exc_info=True)