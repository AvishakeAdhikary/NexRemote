"""
Settings Dialog
Configure application settings
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QLineEdit, QSpinBox, QCheckBox,
                              QGroupBox, QFormLayout, QTabWidget, QWidget,
                              QListWidget, QMessageBox)
from PyQt6.QtCore import Qt
from utils.logger import get_logger

logger = get_logger(__name__)

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        
        # General tab
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "General")
        
        # Network tab
        network_tab = self.create_network_tab()
        tabs.addTab(network_tab, "Network")
        
        # Security tab
        security_tab = self.create_security_tab()
        tabs.addTab(security_tab, "Security")
        
        # Trusted Devices tab
        devices_tab = self.create_devices_tab()
        tabs.addTab(devices_tab, "Trusted Devices")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # PC Name
        self.pc_name_edit = QLineEdit()
        layout.addRow("PC Name:", self.pc_name_edit)
        
        # Auto-start
        self.auto_start_check = QCheckBox("Start with Windows")
        layout.addRow("", self.auto_start_check)
        
        # Minimize to tray
        self.minimize_tray_check = QCheckBox("Minimize to system tray")
        layout.addRow("", self.minimize_tray_check)
        
        # Show notifications
        self.show_notifications_check = QCheckBox("Show connection notifications")
        self.show_notifications_check.setChecked(True)
        layout.addRow("", self.show_notifications_check)
        
        return widget
    
    def create_network_tab(self) -> QWidget:
        """Create network settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Server port
        self.server_port_spin = QSpinBox()
        self.server_port_spin.setRange(1024, 65535)
        self.server_port_spin.setValue(8765)
        layout.addRow("Server Port:", self.server_port_spin)
        
        # Discovery port
        self.discovery_port_spin = QSpinBox()
        self.discovery_port_spin.setRange(1024, 65535)
        self.discovery_port_spin.setValue(37020)
        layout.addRow("Discovery Port:", self.discovery_port_spin)
        
        # Max clients
        self.max_clients_spin = QSpinBox()
        self.max_clients_spin.setRange(1, 10)
        self.max_clients_spin.setValue(5)
        layout.addRow("Max Clients:", self.max_clients_spin)
        
        # Enable remote access
        self.remote_access_check = QCheckBox("Enable remote access (outside local network)")
        layout.addRow("", self.remote_access_check)
        
        return widget
    
    def create_security_tab(self) -> QWidget:
        """Create security settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Require approval
        self.require_approval_check = QCheckBox("Require approval for new connections")
        self.require_approval_check.setChecked(True)
        layout.addRow("", self.require_approval_check)
        
        # Enable audit logging
        self.audit_logging_check = QCheckBox("Enable audit logging")
        self.audit_logging_check.setChecked(True)
        layout.addRow("", self.audit_logging_check)
        
        # Input validation
        self.input_validation_check = QCheckBox("Enable input validation")
        self.input_validation_check.setChecked(True)
        layout.addRow("", self.input_validation_check)
        
        # Certificate info
        cert_group = QGroupBox("Certificate Information")
        cert_layout = QVBoxLayout()
        
        self.cert_info_label = QLabel("Loading certificate info...")
        cert_layout.addWidget(self.cert_info_label)
        
        regenerate_cert_btn = QPushButton("Regenerate Certificate")
        regenerate_cert_btn.clicked.connect(self.regenerate_certificate)
        cert_layout.addWidget(regenerate_cert_btn)
        
        cert_group.setLayout(cert_layout)
        layout.addRow(cert_group)
        
        return widget
    
    def create_devices_tab(self) -> QWidget:
        """Create trusted devices tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel("Trusted Devices:")
        layout.addWidget(label)
        
        self.devices_list = QListWidget()
        layout.addWidget(self.devices_list)
        
        button_layout = QHBoxLayout()
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_trusted_device)
        button_layout.addWidget(remove_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_trusted_devices)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def load_settings(self):
        """Load settings from config"""
        self.pc_name_edit.setText(self.config.get('pc_name', ''))
        self.auto_start_check.setChecked(self.config.get('auto_start', False))
        self.minimize_tray_check.setChecked(self.config.get('minimize_to_tray', True))
        self.server_port_spin.setValue(self.config.get('server_port', 8765))
        self.discovery_port_spin.setValue(self.config.get('discovery_port', 37020))
        self.max_clients_spin.setValue(self.config.get('max_clients', 5))
        self.remote_access_check.setChecked(self.config.get('enable_remote_access', False))
        self.require_approval_check.setChecked(self.config.get('require_approval', True))
        
        # Load trusted devices
        # This would load from the authentication module
        self.load_trusted_devices()
    
    def load_trusted_devices(self):
        """Load list of trusted devices"""
        # TODO: Load from authentication module
        pass
    
    def save_settings(self):
        """Save settings to config"""
        self.config.set('pc_name', self.pc_name_edit.text())
        self.config.set('auto_start', self.auto_start_check.isChecked())
        self.config.set('minimize_to_tray', self.minimize_tray_check.isChecked())
        self.config.set('server_port', self.server_port_spin.value())
        self.config.set('discovery_port', self.discovery_port_spin.value())
        self.config.set('max_clients', self.max_clients_spin.value())
        self.config.set('enable_remote_access', self.remote_access_check.isChecked())
        self.config.set('require_approval', self.require_approval_check.isChecked())
        
        self.config.save()
        logger.info("Settings saved")
        
        self.accept()
    
    def regenerate_certificate(self):
        """Regenerate SSL certificate"""
        reply = QMessageBox.question(
            self,
            "Regenerate Certificate",
            "This will regenerate the SSL certificate. All connected devices will need to re-pair. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Trigger certificate regeneration
            logger.info("Certificate regeneration requested")
    
    def remove_trusted_device(self):
        """Remove selected trusted device"""
        current_item = self.devices_list.currentItem()
        if current_item:
            # TODO: Remove from authentication module
            self.devices_list.takeItem(self.devices_list.row(current_item))
    
    def clear_trusted_devices(self):
        """Clear all trusted devices"""
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Remove all trusted devices? They will need to be re-approved on next connection.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.devices_list.clear()
            # TODO: Clear from authentication module