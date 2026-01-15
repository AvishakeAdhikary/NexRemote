"""
Network server for handling Android client connections
"""
import secrets
import socket
import time
import threading
import json
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from input.mouse_controller import MouseController
from input.keyboard_controller import KeyboardController
from input.gamepad_controller import GamepadController
from screen.capture import ScreenCapture
from file.transfer import FileTransferHandler
from media.player_controller import MediaController
from system.process_manager import ProcessManager

logger = logging.getLogger(__name__)

class ClientHandler(threading.Thread):
    """Handles individual client connection with encryption"""
    
    def __init__(self, client_socket, address, server, client_id):
        super().__init__()
        self.client_socket = client_socket
        self.address = address
        self.server = server
        self.client_id = client_id
        self.running = True
        self.authenticated = False
        self.cipher = None
        self.device_name = "Unknown Device"
        
        # Controllers
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.gamepad = GamepadController()
        self.screen = ScreenCapture()
        self.file_handler = FileTransferHandler()
        self.media = MediaController()
        self.process_manager = ProcessManager()
        
    def run(self):
        """Main client handling loop"""
        logger.info(f"Client handler started for {self.address} (ID: {self.client_id})")
        self.server.log_audit(f"Connection attempt from {self.address}")
        
        try:
            # Perform handshake and authentication
            if not self.handshake():
                logger.warning(f"Handshake failed for {self.address}")
                self.send_message('error', {'message': 'Handshake failed'})
                self.cleanup()
                return
            
            if not self.authenticate():
                logger.warning(f"Authentication failed for {self.address}")
                self.send_message('error', {'message': 'Authentication failed'})
                self.cleanup()
                return
            
            logger.info(f"Client {self.address} authenticated as '{self.device_name}'")
            self.server.log_audit(f"Client authenticated: {self.device_name} ({self.address})")
            
            buffer = b""
            while self.running:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                    
                buffer += data
                
                # Process complete encrypted messages
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        # Decrypt message
                        decrypted = self.cipher.decrypt(line)
                        message = json.loads(decrypted.decode('utf-8'))
                        self.handle_message(message)
                    except Exception as e:
                        logger.error(f"Message processing error: {e}")
                        
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            self.cleanup()
    
    def handshake(self):
        """Perform encryption handshake"""
        try:
            # Generate encryption key
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            
            # Send key to client
            handshake_data = {
                'type': 'handshake',
                'key': key.decode('utf-8'),
                'server_version': '2.0'
            }
            json_str = json.dumps(handshake_data) + '\n'
            self.client_socket.sendall(json_str.encode('utf-8'))
            
            # Wait for acknowledgment
            self.client_socket.settimeout(10)
            data = self.client_socket.recv(1024)
            response = json.loads(data.decode('utf-8'))
            
            if response.get('type') == 'handshake_ack':
                logger.info(f"Handshake completed with {self.address}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Handshake error: {e}")
            return False
    
    def authenticate(self):
        """Authenticate client with pairing code"""
        try:
            # Request authentication
            auth_request = {
                'type': 'auth_request',
                'pairing_required': self.server.require_pairing
            }
            self.send_encrypted(auth_request)
            
            # Wait for auth response
            self.client_socket.settimeout(30)
            data = self.client_socket.recv(1024)
            encrypted_msg = data.strip()
            
            decrypted = self.cipher.decrypt(encrypted_msg)
            auth_data = json.loads(decrypted.decode('utf-8'))
            
            if auth_data.get('type') == 'auth_response':
                pairing_code = auth_data.get('pairing_code', '')
                self.device_name = auth_data.get('device_name', 'Unknown Device')
                
                # Verify pairing code
                if self.server.require_pairing:
                    expected_code = self.server.get_pairing_code()
                    if pairing_code != expected_code:
                        logger.warning(f"Invalid pairing code from {self.address}")
                        self.send_encrypted({'type': 'auth_failed', 'reason': 'Invalid pairing code'})
                        return False
                
                # Check if device is approved
                if not self.server.is_device_approved(self.device_name, self.address):
                    # Request approval from user
                    approval = self.server.request_approval(self.device_name, self.address)
                    if not approval:
                        self.send_encrypted({'type': 'auth_failed', 'reason': 'Connection not approved'})
                        return False
                
                self.authenticated = True
                self.send_encrypted({'type': 'auth_success'})
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def send_encrypted(self, data):
        """Send encrypted message"""
        try:
            json_str = json.dumps(data)
            encrypted = self.cipher.encrypt(json_str.encode('utf-8'))
            self.client_socket.sendall(encrypted + b'\n')
        except Exception as e:
            logger.error(f"Send encrypted error: {e}")
    
    def handle_message(self, message):
        """Handle incoming message from client"""
        if not self.authenticated:
            return
        
        msg_type = message.get('type')
        data = message.get('data', {})
        
        # Log command for audit
        self.server.log_audit(f"{self.device_name}: {msg_type}")
        
        try:
            # Validate input
            if not self.validate_command(msg_type, data):
                logger.warning(f"Invalid command: {msg_type}")
                return
            
            if msg_type == 'mouse_move':
                self.mouse.move(data['dx'], data['dy'])
            elif msg_type == 'mouse_click':
                self.mouse.click(data['button'], data.get('double', False))
            elif msg_type == 'mouse_scroll':
                self.mouse.scroll(data['dx'], data['dy'])
            elif msg_type == 'key_press':
                self.keyboard.press(data['key'])
            elif msg_type == 'key_release':
                self.keyboard.release(data['key'])
            elif msg_type == 'key_type':
                self.keyboard.type_text(data['text'])
            elif msg_type == 'gamepad_button':
                self.gamepad.button(data['button'], data['pressed'])
            elif msg_type == 'gamepad_axis':
                self.gamepad.axis(data['axis'], data['value'])
            elif msg_type == 'gamepad_trigger':
                self.gamepad.trigger(data['trigger'], data['value'])
            elif msg_type == 'screen_start':
                self.start_screen_stream(data.get('quality', 75))
            elif msg_type == 'screen_stop':
                self.stop_screen_stream()
            elif msg_type == 'file_list':
                self.send_file_list(data.get('path', ''))
            elif msg_type == 'file_download':
                self.send_file(data['path'])
            elif msg_type == 'file_upload':
                self.receive_file(data)
            elif msg_type == 'media_play_pause':
                self.media.play_pause()
            elif msg_type == 'media_next':
                self.media.next_track()
            elif msg_type == 'media_prev':
                self.media.prev_track()
            elif msg_type == 'media_volume':
                self.media.volume(data['value'])
            elif msg_type == 'process_list':
                self.send_process_list()
            elif msg_type == 'process_kill':
                self.process_manager.kill_process(data['pid'])
            elif msg_type == 'app_launch':
                self.process_manager.launch_app(data['path'])
            elif msg_type == 'ping':
                self.send_message('pong', {'timestamp': time.time()})
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling message {msg_type}: {e}")
            self.server.log_audit(f"ERROR - {self.device_name}: {msg_type} - {str(e)}")
    
    def validate_command(self, msg_type, data):
        """Validate command and data"""
        # Define required fields for each command
        validators = {
            'mouse_move': ['dx', 'dy'],
            'mouse_click': ['button'],
            'mouse_scroll': ['dx', 'dy'],
            'key_press': ['key'],
            'key_release': ['key'],
            'key_type': ['text'],
            'gamepad_button': ['button', 'pressed'],
            'gamepad_axis': ['axis', 'value'],
            'gamepad_trigger': ['trigger', 'value'],
            'file_download': ['path'],
            'file_upload': ['path', 'content'],
            'process_kill': ['pid'],
            'app_launch': ['path'],
        }
        
        if msg_type in validators:
            required_fields = validators[msg_type]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Missing field '{field}' in {msg_type}")
                    return False
        
        return True
    
    def send_message(self, msg_type, data=None):
        """Send encrypted message to client"""
        try:
            message = {'type': msg_type, 'data': data or {}}
            self.send_encrypted(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    def start_screen_stream(self, quality):
        """Start streaming screen to client"""
        def stream_worker():
            while self.running and hasattr(self, 'streaming') and self.streaming:
                try:
                    frame = self.screen.capture_frame(quality)
                    if frame:
                        self.send_message('screen_frame', {'frame': frame})
                    time.sleep(0.033)  # ~30 FPS
                except Exception as e:
                    logger.error(f"Screen stream error: {e}")
                    break
        
        self.streaming = True
        self.stream_thread = threading.Thread(target=stream_worker, daemon=True)
        self.stream_thread.start()
    
    def stop_screen_stream(self):
        """Stop screen streaming"""
        self.streaming = False
    
    def send_file_list(self, path):
        """Send file list to client"""
        try:
            files = self.file_handler.list_files(path)
            self.send_message('file_list_response', {'files': files})
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            self.send_message('error', {'message': str(e)})
    
    def send_file(self, path):
        """Send file to client"""
        try:
            file_data = self.file_handler.read_file(path)
            self.send_message('file_data', file_data)
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            self.send_message('error', {'message': str(e)})
    
    def receive_file(self, data):
        """Receive file from client"""
        try:
            self.file_handler.write_file(data['path'], data['content'])
            self.send_message('file_upload_success', {'path': data['path']})
        except Exception as e:
            logger.error(f"Error receiving file: {e}")
            self.send_message('error', {'message': str(e)})
    
    def send_process_list(self):
        """Send process list to client"""
        try:
            processes = self.process_manager.get_process_list()
            self.send_message('process_list_response', {'processes': processes})
        except Exception as e:
            logger.error(f"Error getting processes: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.authenticated = False
        self.stop_screen_stream()
        self.gamepad.reset()
        try:
            self.client_socket.close()
        except:
            pass
        
        # Remove from server's client list
        if self.client_id in self.server.clients:
            del self.server.clients[self.client_id]
            self.server.client_disconnected.emit(self.address)
        
        logger.info(f"Client handler closed for {self.address}")
        self.server.log_audit(f"Client disconnected: {self.device_name} ({self.address})")

class ControlServer(QObject):
    """Main control server with multi-client support"""
    
    client_connected = pyqtSignal(str, str)  # address, device_name
    client_disconnected = pyqtSignal(str)
    log_message = pyqtSignal(str)
    approval_requested = pyqtSignal(str, str, object)  # device_name, address, callback
    
    def __init__(self, port=8888):
        super().__init__()
        self.port = port
        self.running = False
        self.server_socket = None
        self.clients = {}
        self.accept_thread = None
        self.next_client_id = 1
        
        # Security settings
        self.require_pairing = True
        self.pairing_code = self.generate_pairing_code()
        self.approved_devices = set()
        self.auto_approve = False
        
        # Audit log
        self.audit_log = []
        
    def generate_pairing_code(self):
        """Generate 6-digit pairing code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    def get_pairing_code(self):
        """Get current pairing code"""
        return self.pairing_code
    
    def regenerate_pairing_code(self):
        """Generate new pairing code"""
        self.pairing_code = self.generate_pairing_code()
        self.log_message.emit(f"New pairing code: {self.pairing_code}")
        return self.pairing_code
    
    def is_device_approved(self, device_name, address):
        """Check if device is approved"""
        if self.auto_approve:
            return True
        device_id = f"{device_name}:{address}"
        return device_id in self.approved_devices
    
    def approve_device(self, device_name, address):
        """Approve a device"""
        device_id = f"{device_name}:{address}"
        self.approved_devices.add(device_id)
        self.log_audit(f"Device approved: {device_name} ({address})")
    
    def request_approval(self, device_name, address):
        """Request user approval for device connection"""
        approval_result = {'approved': False}
        
        def callback(approved):
            approval_result['approved'] = approved
        
        self.approval_requested.emit(device_name, address, callback)
        
        # Wait for approval (with timeout)
        for _ in range(300):  # 30 seconds
            if approval_result['approved']:
                self.approve_device(device_name, address)
                return True
            time.sleep(0.1)
        
        return False
    
    def log_audit(self, message):
        """Log audit message"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.audit_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        
        # Write to file
        try:
            with open('logs/audit.log', 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except:
            pass
        
        logger.info(f"AUDIT: {message}")
    
    def start(self):
        """Start the server"""
        if self.running:
            return
        
        try:
            # Configure Windows Firewall
            self.configure_firewall()
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(10)  # Support up to 10 clients
            self.running = True
            
            self.accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
            self.accept_thread.start()
            
            logger.info(f"Server started on port {self.port}")
            self.log_message.emit(f"Server listening on port {self.port}")
            self.log_message.emit(f"Pairing code: {self.pairing_code}")
            self.log_audit("Server started")
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.log_message.emit(f"Error: {e}")
            raise
    
    def configure_firewall(self):
        """Automatically configure Windows Firewall"""
        try:
            import subprocess
            import sys
            
            # Get Python executable path
            python_exe = sys.executable
            
            # Rule name
            rule_name = "NexRemote_Server"
            
            # Check if rule exists
            check_cmd = f'netsh advfirewall firewall show rule name="{rule_name}"'
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if "No rules match" in result.stdout:
                # Add firewall rule
                add_cmd = (
                    f'netsh advfirewall firewall add rule '
                    f'name="{rule_name}" '
                    f'dir=in action=allow '
                    f'program="{python_exe}" '
                    f'enable=yes '
                    f'profile=private,public'
                )
                
                subprocess.run(add_cmd, shell=True, check=True)
                logger.info("Firewall rule added successfully")
                self.log_message.emit("Firewall configured automatically")
            else:
                logger.info("Firewall rule already exists")
                
        except Exception as e:
            logger.warning(f"Could not configure firewall automatically: {e}")
            self.log_message.emit("Note: You may need to allow this app through firewall manually")
    
    def accept_clients(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, address = self.server_socket.accept()
                address_str = f"{address[0]}:{address[1]}"
                
                client_id = self.next_client_id
                self.next_client_id += 1
                
                handler = ClientHandler(client_socket, address_str, self, client_id)
                handler.start()
                
                self.clients[client_id] = handler
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")
                break
    
    def stop(self):
        """Stop the server"""
        if not self.running:
            return
        
        self.running = False
        
        # Close all client connections
        for client_id, handler in list(self.clients.items()):
            handler.running = False
            try:
                handler.join(timeout=2)
            except:
                pass
        
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("Server stopped")
        self.log_message.emit("Server stopped")
        self.log_audit("Server stopped")