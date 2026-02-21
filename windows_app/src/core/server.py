"""
WebSocket Server with TLS support
Handles multiple client connections with concurrent message processing.
Uses binary WebSocket frames for high-performance screen/camera streaming.
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
from streaming.camera_streamer import CameraStreamer
from ui.file_explorer import FileExplorer
from ui.task_manager import TaskManager
from utils.logger import get_logger
from utils.protocol import MessageHandler

logger = get_logger(__name__)

# Binary frame headers (4 bytes)
SCREEN_HEADER = b'SCRN'
CAMERA_HEADER = b'CAMF'


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
        
        # Streaming
        self.screen_capture = ScreenCapture(config)
        self.camera_streamer = CameraStreamer(config)
        
        # File system and process management
        self.file_explorer = FileExplorer(config)
        self.task_manager = TaskManager()
        
        # Active connections
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Active streaming tasks per client
        # screen tasks keyed by (client_id, mss_monitor_index) for multi-monitor
        self._screen_stream_tasks: dict[tuple[str, int], asyncio.Task] = {}
        self._camera_stream_tasks: Dict[str, asyncio.Task] = {}
        self._media_stream_tasks:  Dict[str, asyncio.Task] = {}
        
        logger.info("Server initialized")
    
    async def start(self):
        """Start the server(s)"""
        try:
            self.running = True
            
            # Start the screen capture thread (always running — low cost when idle)
            self.screen_capture.start()
            
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
                max_size=50 * 1024 * 1024,  # 50 MB for binary frames
                ping_interval=20,
                ping_timeout=10
            ):
                logger.info(f"Secure server (WSS) listening on port {port}")
                await asyncio.Future()  # Run forever
        except Exception as e:
            logger.error(f"Secure server error: {e}", exc_info=True)
    
    async def start_non_secure_server(self):
        """Start non-secure WebSocket server (WS)"""
        try:
            port = self.config.get('server_port_insecure', 8766)
            
            async with websockets.serve(
                self.handle_client,
                "0.0.0.0",
                port,
                ssl=None,
                max_size=50 * 1024 * 1024,  # 50 MB for binary frames
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
            
            # Handle messages — dispatch each to its own task for concurrency
            async for message in websocket:
                asyncio.create_task(self._safe_process(client_id, message))
                
        except asyncio.TimeoutError:
            logger.warning("Client authentication timeout")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {device_name}")
        except Exception as e:
            logger.error(f"Error handling client: {e}", exc_info=True)
        finally:
            # Cleanup: stop streaming for this client
            self._stop_client_streams(client_id)
            
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                self.client_disconnected.emit(client_id)
                self.audit_logger.log_event("client_disconnected", {"client_id": client_id})
    
    async def _safe_process(self, client_id: str, message):
        """Wrapper to catch exceptions in create_task'd message processing"""
        try:
            await self.process_message(client_id, message)
        except Exception as e:
            logger.error(f"Unhandled error processing message from {client_id}: {e}", exc_info=True)
    
    async def process_message(self, client_id: str, message):
        """Process incoming message from client (runs as independent task)"""
        msg_type = 'unknown'
        try:
            # Decrypt message
            decrypted = self.encryption.decrypt(message)
            data = json.loads(decrypted)
            
            msg_type = data.get('type', 'unknown')
            
            # Validate input
            if not self.input_validator.validate(data):
                logger.warning(f"Invalid message from {client_id}: {msg_type}")
                return
            
            # Route to appropriate handler
            if msg_type == 'keyboard':
                self.keyboard.send_key(data)
            elif msg_type == 'mouse':
                self.mouse.send_input(data)
            elif msg_type == 'gamepad':
                self.gamepad.send_input(data)
            elif msg_type == 'camera':
                await self._handle_camera(client_id, data)
            elif msg_type == 'file_explorer':
                # Offload blocking I/O to thread pool
                response = await asyncio.to_thread(self.file_explorer.handle_request, data)
                await self._send_response(client_id, response)
            elif msg_type == 'screen_share':
                await self._handle_screen_share(client_id, data)
            elif msg_type == 'media_control':
                await self._handle_media_control(client_id, data)
            elif msg_type == 'task_manager':
                # Offload blocking psutil calls to thread pool
                response = await asyncio.to_thread(self.task_manager.handle_request, data)
                await self._send_response(client_id, response)
            elif msg_type == 'clipboard':
                self.handle_clipboard(data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
            
            # Emit signal (may fail if no UI connected)
            try:
                self.message_received.emit(client_id, data)
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Error processing message type '{msg_type}': {type(e).__name__}: {e}")
    
    # ─── Screen Share (push-model binary streaming) ────────────────────
    
    async def _handle_screen_share(self, client_id: str, data: dict):
        """Handle screen share requests with full multi-monitor support."""
        try:
            action = data.get('action')

            if action == 'start':
                fps        = data.get('fps', 30)
                quality    = data.get('quality', 70)
                resolution = data.get('resolution', 'native')

                # Supports both single display_index and a list display_indices
                single = data.get('display_index', 0)
                indices: list[int] = data.get('display_indices', [single])
                if not indices:
                    indices = [single]

                self.screen_capture.set_fps(fps)
                self.screen_capture.set_quality(quality)
                self.screen_capture.set_resolution(resolution)

                for disp_idx in indices:
                    # mss is 1-based; disp_idx 0 → mss monitor 1
                    mss_idx = max(1, disp_idx + 1)
                    key = (client_id, mss_idx)

                    # Cancel existing push for this monitor
                    if key in self._screen_stream_tasks:
                        self._screen_stream_tasks[key].cancel()

                    # Start per-monitor capture thread
                    self.screen_capture.start_monitor(mss_idx)

                    # Start push loop for this monitor
                    task = asyncio.create_task(
                        self._screen_push_loop(client_id, mss_idx, fps)
                    )
                    self._screen_stream_tasks[key] = task

                logger.info(
                    f"Screen streaming started for {client_id} "
                    f"monitors={indices} ({resolution}, {fps}fps, q{quality})"
                )

            elif action == 'stop':
                # Stop all monitors for this client (or specific one)
                stop_idx = data.get('display_index', None)
                keys_to_cancel = [
                    k for k in self._screen_stream_tasks
                    if k[0] == client_id and (stop_idx is None or k[1] == stop_idx + 1)
                ]
                for k in keys_to_cancel:
                    self._screen_stream_tasks[k].cancel()
                    del self._screen_stream_tasks[k]
                    self.screen_capture.stop_monitor(k[1])
                logger.info(f"Screen streaming stopped for {client_id}")

            elif action == 'set_quality':
                self.screen_capture.set_quality(data.get('quality', 70))

            elif action == 'set_resolution':
                self.screen_capture.set_resolution(data.get('resolution', 'native'))

            elif action == 'set_fps':
                new_fps = data.get('fps', 30)
                self.screen_capture.set_fps(new_fps)
                # Restart all push loops for this client with new FPS
                for key in [k for k in self._screen_stream_tasks if k[0] == client_id]:
                    self._screen_stream_tasks[key].cancel()
                    task = asyncio.create_task(
                        self._screen_push_loop(client_id, key[1], new_fps)
                    )
                    self._screen_stream_tasks[key] = task

            elif action == 'set_monitor':
                self.screen_capture.set_monitor(data.get('monitor_index', 1))

            elif action == 'list_displays':
                monitors = await asyncio.to_thread(self.screen_capture.get_monitors)
                display_list = []
                for m in monitors:
                    display_list.append({
                        'index':      m['id'] - 1,   # 0-based for client
                        'name':       m.get('label', f"Display {m['id']}"),
                        'width':      m['width'],
                        'height':     m['height'],
                        'is_primary': m.get('is_primary', False),
                    })
                if not display_list:
                    display_list = [{
                        'index': 0, 'name': 'Primary Display',
                        'width': 1920, 'height': 1080, 'is_primary': True,
                    }]
                info = self.screen_capture.get_frame_info()
                active = [idx - 1 for idx in self.screen_capture.get_all_active_monitors()]
                response = {
                    'type': 'screen_share',
                    'action': 'display_list',
                    'displays': display_list,
                    'active_displays': active,
                    'current_resolution': info['resolution'],
                    'current_fps': info['fps'],
                    'current_quality': info['quality'],
                }
                await self._send_response(client_id, response)

            elif action == 'input':
                self._handle_screen_share_input(data)

        except Exception as e:
            logger.error(f"Error handling screen share: {e}", exc_info=True)
    
    async def _screen_push_loop(self, client_id: str, monitor_index: int, fps: int):
        """
        Push JPEG frames for one monitor to the client as binary messages.
        Header: SCRN (4 bytes) + monitor_index as 1 byte = 5-byte header total.
        The client reads byte[4] to route the frame to the correct display slot.
        """
        interval = 1.0 / max(1, fps)
        logger.debug(
            f"Screen push loop started for {client_id} "
            f"monitor={monitor_index} ({fps} fps)"
        )
        # Build per-monitor header: SCRN + monitor_index (1 byte, 0-based for client)
        client_mon_idx = max(0, monitor_index - 1).to_bytes(1, 'big')
        header = SCREEN_HEADER + client_mon_idx

        try:
            while client_id in self.clients:
                t0 = asyncio.get_event_loop().time()

                frame = self.screen_capture.get_latest_frame(monitor_index)
                if frame and client_id in self.clients:
                    try:
                        await self.clients[client_id].send(header + frame)
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except Exception as e:
                        logger.error(f"Error sending screen frame: {e}")
                        break

                elapsed = asyncio.get_event_loop().time() - t0
                wait = interval - elapsed
                await asyncio.sleep(max(0.0, wait))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Screen push loop error: {e}", exc_info=True)
        finally:
            logger.debug(
                f"Screen push loop ended {client_id} monitor={monitor_index}"
            )

    # ─── Media Control (state sync) ────────────────────────────────────

    async def _handle_media_control(self, client_id: str, data: dict):
        """Handle media commands and manage the per-client media state push loop."""
        action = data.get('action')

        # Execute the command in a thread (COM + subprocess calls are blocking)
        response = await asyncio.to_thread(self.media_controller.send_command, data)

        # For get_info, send the result back immediately
        if response:
            await self._send_response(client_id, response)

        # Start the push loop on first interaction with this client, if not already running
        if client_id not in self._media_stream_tasks or \
                self._media_stream_tasks[client_id].done():
            task = asyncio.create_task(self._media_push_loop(client_id))
            self._media_stream_tasks[client_id] = task
            logger.debug(f"Media push loop started for {client_id}")

    async def _media_push_loop(self, client_id: str):
        """
        Push the full media state (volume, mute, now-playing) to the client every
        1.5 seconds while it is connected. This keeps the Flutter UI always in sync
        with actual Windows state without the client needing to poll.
        """
        logger.debug(f"Media state push loop running for {client_id}")
        try:
            while client_id in self.clients:
                try:
                    state = await asyncio.to_thread(
                        self.media_controller.get_full_state
                    )
                    await self._send_response(client_id, state)
                except Exception as e:
                    logger.debug(f"Media state push error: {e}")

                # Poll at 1.5 s — fast enough to feel real-time, slow enough not
                # to hammer PowerShell for SMTC data on every tick
                await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            pass
        finally:
            logger.debug(f"Media push loop ended for {client_id}")
    
    # ─── Camera (server→client streaming) ──────────────────────────────
    
    async def _handle_camera(self, client_id: str, data: dict):
        """Handle camera requests — stream FROM PC cameras TO client"""
        try:
            action = data.get('action')
            
            if action == 'list_cameras':
                cameras = await asyncio.to_thread(self.camera_streamer.list_cameras)
                response = {
                    'type': 'camera',
                    'action': 'camera_list',
                    'cameras': cameras,
                }
                await self._send_response(client_id, response)
                
            elif action == 'start':
                camera_index = data.get('camera_index', 0)
                
                # Start camera capture thread
                await asyncio.to_thread(self.camera_streamer.start, camera_index)
                
                # Cancel any existing camera stream for this client
                if client_id in self._camera_stream_tasks:
                    self._camera_stream_tasks[client_id].cancel()
                
                # Launch push loop
                task = asyncio.create_task(self._camera_push_loop(client_id))
                self._camera_stream_tasks[client_id] = task
                
                # Send camera info back
                info = self.camera_streamer.get_camera_info()
                response = {
                    'type': 'camera',
                    'action': 'started',
                    'camera_info': info,
                }
                await self._send_response(client_id, response)
                logger.info(f"Camera streaming started for {client_id} (camera {camera_index})")
                
            elif action == 'stop':
                if client_id in self._camera_stream_tasks:
                    self._camera_stream_tasks[client_id].cancel()
                    del self._camera_stream_tasks[client_id]
                await asyncio.to_thread(self.camera_streamer.stop)
                logger.info(f"Camera streaming stopped for {client_id}")
                
            elif action == 'set_camera':
                camera_index = data.get('camera_index', 0)
                # Restart with new camera
                was_streaming = client_id in self._camera_stream_tasks
                if was_streaming:
                    self._camera_stream_tasks[client_id].cancel()
                
                await asyncio.to_thread(self.camera_streamer.start, camera_index)
                
                if was_streaming:
                    task = asyncio.create_task(self._camera_push_loop(client_id))
                    self._camera_stream_tasks[client_id] = task
                
                info = self.camera_streamer.get_camera_info()
                response = {
                    'type': 'camera',
                    'action': 'camera_changed',
                    'camera_info': info,
                }
                await self._send_response(client_id, response)
                
        except Exception as e:
            logger.error(f"Error handling camera: {e}", exc_info=True)
    
    async def _camera_push_loop(self, client_id: str):
        """Push camera frames to client as binary messages"""
        logger.debug(f"Camera push loop started for {client_id}")
        
        try:
            while client_id in self.clients and self.camera_streamer.is_active:
                start = asyncio.get_event_loop().time()
                
                frame = self.camera_streamer.get_latest_frame()
                
                if frame and client_id in self.clients:
                    try:
                        # Send as binary: CAMF header + JPEG bytes
                        await self.clients[client_id].send(CAMERA_HEADER + frame)
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except Exception as e:
                        logger.error(f"Error sending camera frame: {e}")
                        break
                
                # Pace to camera FPS
                info = self.camera_streamer.get_camera_info()
                fps = info.get('fps', 30) or 30
                interval = 1.0 / fps
                elapsed = asyncio.get_event_loop().time() - start
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    await asyncio.sleep(0)
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Camera push loop error: {e}", exc_info=True)
        finally:
            logger.debug(f"Camera push loop ended for {client_id}")
    
    # ─── Utility ───────────────────────────────────────────────────────
    
    def _stop_client_streams(self, client_id: str):
        """Cancel all streaming tasks for a client"""
        # Screen tasks are keyed (client_id, monitor_index)
        screen_keys = [k for k in self._screen_stream_tasks if k[0] == client_id]
        for k in screen_keys:
            self._screen_stream_tasks[k].cancel()
            del self._screen_stream_tasks[k]

        for task_dict in (self._camera_stream_tasks, self._media_stream_tasks):
            if client_id in task_dict:
                task_dict[client_id].cancel()
                del task_dict[client_id]
    
    async def _send_response(self, client_id: str, response: dict):
        """Send an encrypted JSON response back to a specific client"""
        try:
            if client_id not in self.clients:
                return
            
            message = json.dumps(response)
            encrypted = self.encryption.encrypt(message)
            # IMPORTANT: encrypted is bytes (base64). Decode to str so websockets
            # sends a text frame, not binary. Flutter routes binary frames to
            # binaryMessageController (screen/camera), not messageController.
            if isinstance(encrypted, bytes):
                encrypted = encrypted.decode('utf-8')
            await self.clients[client_id].send(encrypted)
        except Exception as e:
            logger.error(f"Error sending response to {client_id}: {e}")

    
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """Broadcast message to all connected clients"""
        exclude = exclude or set()
        encrypted = self.encryption.encrypt(json.dumps(message))
        if isinstance(encrypted, bytes):
            encrypted = encrypted.decode('utf-8')

        
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
            "camera_streaming": True,
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
        
        # Cancel all streaming tasks
        for task in list(self._screen_stream_tasks.values()):
            task.cancel()
        self._screen_stream_tasks.clear()
        
        for task in list(self._camera_stream_tasks.values()):
            task.cancel()
        self._camera_stream_tasks.clear()
        
        # Close all client connections
        for client_id, ws in list(self.clients.items()):
            try:
                asyncio.ensure_future(ws.close())
            except Exception:
                pass
        self.clients.clear()
        
        # Stop discovery service
        try:
            self.discovery.stop()
        except Exception:
            pass
        
        # Stop capture threads
        try:
            self.screen_capture.stop()
        except Exception:
            pass
        try:
            self.camera_streamer.stop()
        except Exception:
            pass
        
        logger.info("Server stopped")
    
    def handle_clipboard(self, data):
        """Handle clipboard sync"""
        pass
    
    def _handle_screen_share_input(self, data: dict):
        """Handle touch input from screen share interactive mode — routes to VirtualMouse"""
        try:
            input_action = data.get('input_action')
            
            if input_action == 'click':
                x = data.get('x', 0)
                y = data.get('y', 0)
                self.mouse.send_input({
                    'action': 'move',
                    'x': x,
                    'y': y,
                })
                self.mouse.send_input({
                    'action': 'click',
                    'button': data.get('button', 'left'),
                    'count': data.get('count', 1),
                })
            elif input_action == 'press':
                x = data.get('x', 0)
                y = data.get('y', 0)
                self.mouse.send_input({
                    'action': 'move',
                    'x': x,
                    'y': y,
                })
                self.mouse.send_input({
                    'action': 'press',
                    'button': data.get('button', 'left'),
                })
            elif input_action == 'release':
                self.mouse.send_input({
                    'action': 'release',
                    'button': data.get('button', 'left'),
                })
            elif input_action == 'move':
                x = data.get('x', 0)
                y = data.get('y', 0)
                self.mouse.send_input({
                    'action': 'move',
                    'x': x,
                    'y': y,
                })
            elif input_action == 'scroll':
                x = data.get('x', 0)
                y = data.get('y', 0)
                self.mouse.send_input({
                    'action': 'move',
                    'x': x,
                    'y': y,
                })
                self.mouse.send_input({
                    'action': 'scroll',
                    'dx': data.get('dx', 0),
                    'dy': data.get('dy', 0),
                })
        except Exception as e:
            logger.error(f"Error handling screen share input: {e}", exc_info=True)