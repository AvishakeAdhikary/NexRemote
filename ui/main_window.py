"""
Main Window UI for Windows Application
"""
import socket
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QGroupBox, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon
from network.server import ControlServer
from network.discovery import DiscoveryService
from utils.config import Config

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.server = None
        self.discovery = None
        self.init_ui()
        self.setup_services()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("NexRemote - PC Server")
        self.setGeometry(100, 100, 600, 500)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Status group
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Status: Stopped")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self.status_label)
        
        # Get local IP
        self.ip_label = QLabel(f"PC IP: {self.get_local_ip()}")
        status_layout.addWidget(self.ip_label)
        
        self.port_label = QLabel(f"Port: {self.config.get('server_port', 8888)}")
        status_layout.addWidget(self.port_label)
        
        self.client_label = QLabel("Connected Clients: 0")
        status_layout.addWidget(self.client_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.start_server)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.show_settings)
        btn_layout.addWidget(settings_btn)
        
        layout.addLayout(btn_layout)
        
        # Log group
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # System tray
        self.setup_tray()
        
        self.log("Application started")
        
    def setup_tray(self):
        """Setup system tray icon"""
        self.tray = QSystemTrayIcon(self)
        # self.tray.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)
        
        self.tray.setContextMenu(tray_menu)
        self.tray.show()
        
    def setup_services(self):
        """Initialize server and discovery services"""
        port = self.config.get('server_port', 8888)
        self.server = ControlServer(port)
        self.server.client_connected.connect(self.on_client_connected)
        self.server.client_disconnected.connect(self.on_client_disconnected)
        self.server.log_message.connect(self.log)
        
        self.discovery = DiscoveryService(port)
        self.discovery.log_message.connect(self.log)
        
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    @pyqtSlot()
    def start_server(self):
        """Start the control server"""
        try:
            self.server.start()
            self.discovery.start()
            self.status_label.setText("Status: Running")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: green;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.log("Server started successfully")
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.log(f"Error: {e}")
    
    @pyqtSlot()
    def stop_server(self):
        """Stop the control server"""
        try:
            self.server.stop()
            self.discovery.stop()
            self.status_label.setText("Status: Stopped")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.client_label.setText("Connected Clients: 0")
            self.log("Server stopped")
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
    
    @pyqtSlot(str)
    def on_client_connected(self, address):
        """Handle client connection"""
        count = len(self.server.clients)
        self.client_label.setText(f"Connected Clients: {count}")
        self.log(f"Client connected: {address}")
    
    @pyqtSlot(str)
    def on_client_disconnected(self, address):
        """Handle client disconnection"""
        count = len(self.server.clients)
        self.client_label.setText(f"Connected Clients: {count}")
        self.log(f"Client disconnected: {address}")
    
    @pyqtSlot(str)
    def log(self, message):
        """Add message to log"""
        self.log_text.append(message)
        
    def show_settings(self):
        """Show settings dialog"""
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config.save()
            self.log("Settings saved")
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.server and self.server.running:
            self.stop_server()
        event.accept()