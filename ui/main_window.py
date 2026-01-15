"""
Main Window UI for Windows Application
"""
import socket
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, 
                             QPushButton, QLabel, QTextEdit, QGroupBox, QSystemTrayIcon, QMenu, QDialog, QDialogButtonBox, QStyle)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon, QFont
from network.server import ControlServer
from network.discovery import DiscoveryService
from utils.config import Config

logger = logging.getLogger(__name__)

class ApprovalDialog(QDialog):
    """Dialog for approving/rejecting device connections"""
    
    def __init__(self, device_name, address, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Request")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        message = QLabel(
            f"Device '{device_name}' from {address}\n"
            f"is requesting permission to connect.\n\n"
            f"Do you want to allow this connection?"
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Yes | QDialogButtonBox.No
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)

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
        self.setWindowTitle("NexRemote - PC Server v2.0")
        self.setGeometry(100, 100, 700, 600)
        
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
        
        # Pairing code group
        pairing_group = QGroupBox("Pairing Code")
        pairing_layout = QVBoxLayout()
        
        self.pairing_label = QLabel("------")
        pairing_font = QFont()
        pairing_font.setPointSize(24)
        pairing_font.setBold(True)
        self.pairing_label.setFont(pairing_font)
        self.pairing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pairing_label.setStyleSheet("color: #4CAF50; background-color: #2b2b2b; padding: 10px;")
        pairing_layout.addWidget(self.pairing_label)
        
        refresh_pairing_btn = QPushButton("Generate New Code")
        refresh_pairing_btn.clicked.connect(self.refresh_pairing_code)
        pairing_layout.addWidget(refresh_pairing_btn)
        
        pairing_note = QLabel("Enter this code on your Android device to connect")
        pairing_note.setStyleSheet("color: gray; font-size: 10px;")
        pairing_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pairing_layout.addWidget(pairing_note)
        
        pairing_group.setLayout(pairing_layout)
        layout.addWidget(pairing_group)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.start_server)
        self.start_btn.setStyleSheet("background-color: #4CAF50; font-weight: bold; padding: 10px;")
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; font-weight: bold; padding: 10px;")
        btn_layout.addWidget(self.stop_btn)
        
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setStyleSheet("padding: 10px;")
        btn_layout.addWidget(settings_btn)
        
        layout.addLayout(btn_layout)
        
        # Log group
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_log_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # System tray
        self.setup_tray()
        
        self.log("Application started - NexRemote v2.0")
        self.log("Features: Encryption, Authentication, Multi-client support")
        
    def setup_tray(self):
        """Setup system tray icon"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
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
        
        # Connect signals
        self.server.client_connected.connect(self.on_client_connected)
        self.server.client_disconnected.connect(self.on_client_disconnected)
        self.server.log_message.connect(self.log)
        self.server.approval_requested.connect(self.on_approval_requested)
        
        # Apply config
        self.server.require_pairing = self.config.get('require_pairing', True)
        self.server.auto_approve = self.config.get('auto_approve', False)
        
        self.discovery = DiscoveryService(port)
        
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
            
            # Update UI
            self.status_label.setText("Status: Running")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: green;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # Show pairing code
            pairing_code = self.server.get_pairing_code()
            self.pairing_label.setText(pairing_code)
            
            self.log("Server started successfully")
            self.log(f"Pairing code: {pairing_code}")
            self.log("Waiting for Android devices to connect...")
            
            # Show notification
            self.tray.showMessage(
                "Server Started",
                f"Pairing code: {pairing_code}",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.log(f"Error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start server:\n{e}")
    
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
            self.pairing_label.setText("------")
            
            self.log("Server stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
    
    @pyqtSlot()
    def refresh_pairing_code(self):
        """Generate new pairing code"""
        if self.server and self.server.running:
            new_code = self.server.regenerate_pairing_code()
            self.pairing_label.setText(new_code)
            self.log(f"New pairing code generated: {new_code}")
        else:
            self.log("Start server first to generate pairing code")
    
    @pyqtSlot(str, str)
    def on_client_connected(self, address, device_name):
        """Handle client connection"""
        count = len(self.server.clients)
        self.client_label.setText(f"Connected Clients: {count}")
        self.log(f"Client connected: {device_name} ({address})")
        
        self.tray.showMessage(
            "Client Connected",
            f"{device_name} connected",
            QSystemTrayIcon.Information,
            2000
        )
    
    @pyqtSlot(str)
    def on_client_disconnected(self, address):
        """Handle client disconnection"""
        count = len(self.server.clients)
        self.client_label.setText(f"Connected Clients: {count}")
        self.log(f"Client disconnected: {address}")
    
    @pyqtSlot(str, str, object)
    def on_approval_requested(self, device_name, address, callback):
        """Handle connection approval request"""
        self.log(f"Approval requested: {device_name} ({address})")
        
        dialog = ApprovalDialog(device_name, address, self)
        result = dialog.exec_()
        
        approved = result == QDialog.Accepted
        callback(approved)
        
        if approved:
            self.log(f"Connection approved: {device_name}")
        else:
            self.log(f"Connection rejected: {device_name}")
    
    @pyqtSlot(str)
    def log(self, message):
        """Add message to log"""
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    @pyqtSlot()
    def clear_log(self):
        """Clear the activity log"""
        self.log_text.clear()
        
    def show_settings(self):
        """Show settings dialog"""
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config.save()
            self.log("Settings saved")
            
            # Update server config
            if self.server:
                self.server.require_pairing = self.config.get('require_pairing', True)
                self.server.auto_approve = self.config.get('auto_approve', False)
            
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved.\nRestart the server for changes to take effect."
            )
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.server and self.server.running:
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                'Server is running. Stop server and exit?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_server()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()