"""
Network server for handling Android client connections
"""
import socket
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
    """Handles individual client connection"""
    
    def __init__(self, client_socket, address, server):
        super().__init__()
        self.client_socket = client_socket
        self.address = address
        self.server = server
        self.running = True
        
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
        logger.info(f"Client handler started for {self.address}")
        buffer = b""
        
        try:
            while self.running:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                    
                buffer += data
                
                # Process complete JSON messages
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        message = json.loads(line.decode('utf-8'))
                        self.handle_message(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            self.cleanup()
    
    def handle_message(self, message):
        """Handle incoming message from client"""
        msg_type = message.get('type')
        data = message.get('data', {})
        
        try:
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
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling message {msg_type}: {e}")
    
    def send_message(self, msg_type, data=None):
        """Send message to client"""
        try:
            message = {'type': msg_type, 'data': data or {}}
            json_str = json.dumps(message) + '\n'
            self.client_socket.sendall(json_str.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    def start_screen_stream(self, quality):
        """Start streaming screen to client"""
        def stream_worker():
            while self.running and hasattr(self, 'streaming'):
                try:
                    frame = self.screen.capture_frame(quality)
                    if frame:
                        self.send_message('screen_frame', {'frame': frame})
                except Exception as e:
                    logger.error(f"Screen stream error: {e}")
                    break
        
        self.streaming = True
        self.stream_thread = threading.Thread(target=stream_worker)
        self.stream_thread.start()
    
    def stop_screen_stream(self):
        """Stop screen streaming"""
        self.streaming = False
        if hasattr(self, 'stream_thread'):
            self.stream_thread.join(timeout=2)
    
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
        self.stop_screen_stream()
        self.gamepad.reset()
        try:
            self.client_socket.close()
        except:
            pass
        logger.info(f"Client handler closed for {self.address}")

class ControlServer(QObject):
    """Main control server"""
    
    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self, port=8888):
        super().__init__()
        self.port = port
        self.running = False
        self.server_socket = None
        self.clients = {}
        self.accept_thread = None
        
    def start(self):
        """Start the server"""
        if self.running:
            return
            
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(5)
        self.running = True
        
        self.accept_thread = threading.Thread(target=self.accept_clients)
        self.accept_thread.start()
        
        logger.info(f"Server started on port {self.port}")
        self.log_message.emit(f"Server listening on port {self.port}")
    
    def accept_clients(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, address = self.server_socket.accept()
                address_str = f"{address[0]}:{address[1]}"
                
                handler = ClientHandler(client_socket, address_str, self)
                handler.start()
                
                self.clients[address_str] = handler
                self.client_connected.emit(address_str)
                
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
        for address, handler in list(self.clients.items()):
            handler.running = False
            handler.join(timeout=2)
            self.client_disconnected.emit(address)
        
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.accept_thread:
            self.accept_thread.join(timeout=2)
        
        logger.info("Server stopped")
        self.log_message.emit("Server stopped")