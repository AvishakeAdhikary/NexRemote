"""
Main Application Window
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QListWidget, QGroupBox,
                              QSystemTrayIcon, QMenu, QMessageBox, QListWidgetItem,
                              QApplication)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon, QAction
import os
from ui.settings_dialog import SettingsDialog
from ui.connection_dialog import ConnectionApprovalDialog
from ui.tray_icon import TrayIcon
from utils.logger import get_logger

logger = get_logger(__name__)



class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, server, config):
        super().__init__()
        self.server = server
        self.config = config
        
        self.setWindowTitle("NexRemote")
        self.setMinimumSize(600, 400)
        
        # Set window icon from local assets
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'images', 'logo.png')
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        
        # Connect signals
        self.server.client_connected.connect(self.on_client_connected)
        self.server.client_disconnected.connect(self.on_client_disconnected)
        
        self.setup_ui()
        self.setup_tray_icon()
        
    def setup_ui(self):
        """Setup user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Status section
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Server Running")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        # PC info
        pc_name = self.config.get('pc_name', 'Unknown PC')
        self.pc_info_label = QLabel(f"PC Name: {pc_name}")
        status_layout.addWidget(self.pc_info_label)
        
        # Port info
        port = self.config.get('server_port', 8765)
        self.port_label = QLabel(f"Port: {port}")
        status_layout.addWidget(self.port_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Connected clients section
        clients_group = QGroupBox("Connected Devices")
        clients_layout = QVBoxLayout()
        
        self.clients_list = QListWidget()
        clients_layout.addWidget(self.clients_list)
        
        clients_group.setLayout(clients_layout)
        layout.addWidget(clients_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_btn)
        
        self.about_btn = QPushButton("About")
        self.about_btn.clicked.connect(self.show_about)
        button_layout.addWidget(self.about_btn)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_tray_icon(self):
        """Setup system tray icon"""
        self.tray = TrayIcon(self)
        self.tray.show_requested.connect(self.show)
        self.tray.hide_requested.connect(self.hide)
        self.tray.quit_requested.connect(self.quit_application)
        self.tray.show()
        
        # Update initial status
        self.tray.update_status("No clients connected")
    
    @pyqtSlot(str, str)
    def on_client_connected(self, client_id: str, device_name: str):
        """Handle client connection"""
        item = QListWidgetItem(f"{device_name} ({client_id[:8]}...)")
        item.setData(Qt.ItemDataRole.UserRole, client_id)
        self.clients_list.addItem(item)
        
        self.statusBar().showMessage(f"Device connected: {device_name}")
        
        # Show notification
        self.tray.show_message(
            "Device Connected",
            f"{device_name} has connected",
            duration=3000
        )
        
        # Update client count
        self.tray.update_client_count(self.clients_list.count())
    
    @pyqtSlot(str)
    def on_client_disconnected(self, client_id: str):
        """Handle client disconnection"""
        for i in range(self.clients_list.count()):
            item = self.clients_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == client_id:
                self.clients_list.takeItem(i)
                break
        
        self.statusBar().showMessage("Device disconnected")
        self.tray.update_client_count(self.clients_list.count())
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # Settings saved
            logger.info("Settings updated")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About NexRemote",
            "NexRemote Clone\n\n"
            "Version 1.0.0\n\n"
            "A complete PC remote control application\n"
            "supporting gamepad, keyboard, mouse, and more."
        )
    
    def quit_application(self):
        """Quit the application — no confirmation dialog for service-like behavior"""
        import os
        logger.info("Quit requested from tray/menu")
        
        # Stop server
        try:
            self.server.stop()
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
        
        # Hide tray icon
        try:
            self.tray.hide()
        except Exception:
            pass
        
        # Quit Qt
        QApplication.quit()
        
        # Force exit after a short delay if Qt didn't close everything
        import threading
        def force_exit():
            import time
            time.sleep(3)
            logger.warning("Force exiting — cleanup timeout")
            os._exit(0)
        threading.Thread(target=force_exit, daemon=True).start()
    
    def closeEvent(self, event):
        """Handle window close event — minimize to tray"""
        event.ignore()
        self.hide()
        
        self.tray.show_message(
            "NexRemote",
            "Application minimized to system tray",
            duration=2000
        )