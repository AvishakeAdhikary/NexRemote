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
from utils.vigem_setup import is_vigem_installed, open_vigem_guide

logger = get_logger(__name__)

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config, authenticator=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.authenticator = authenticator
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
        
        # Gamepad tab
        gamepad_tab = self.create_gamepad_tab()
        tabs.addTab(gamepad_tab, "Gamepad")
        
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
        
        # View Terms & Privacy Policy
        terms_btn = QPushButton("View Terms && Privacy Policy")
        terms_btn.clicked.connect(self._show_terms)
        layout.addRow("", terms_btn)
        
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
        
        # Firewall network profile
        from PyQt6.QtWidgets import QComboBox
        self.firewall_profile_combo = QComboBox()
        self.firewall_profile_combo.addItems([
            "Private networks only (recommended)",
            "Private + Public networks",
            "All profiles (domain, private, public)",
        ])
        # Load saved profile index
        _profile_index = {
            'private': 0,
            'public': 1,
            'all': 2,
        }.get(self.config.get('firewall_profile', 'private'), 0)
        self.firewall_profile_combo.setCurrentIndex(_profile_index)
        layout.addRow("Network Access:", self.firewall_profile_combo)
        
        # Firewall configuration button (triggers UAC)
        firewall_btn = QPushButton("Configure Firewall (requires permission)")
        firewall_btn.clicked.connect(self._configure_firewall)
        layout.addRow("", firewall_btn)
        
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
    
    def create_gamepad_tab(self) -> QWidget:
        """Create gamepad settings tab with ViGEmBus driver status."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Driver status
        driver_group = QGroupBox("ViGEmBus Driver")
        driver_layout = QFormLayout()

        installed = is_vigem_installed()
        status_label = QLabel(
            "✓ Installed" if installed else "✗ Not Installed"
        )
        status_label.setStyleSheet(
            "color: #27ae60; font-weight: bold;" if installed
            else "color: #e74c3c; font-weight: bold;"
        )
        driver_layout.addRow("Status:", status_label)

        if not installed:
            guide_btn = QPushButton("Open Install Guide")
            guide_btn.setStyleSheet(
                "QPushButton { background-color: #3498db; color: white; "
                "padding: 6px 12px; border-radius: 4px; }"
                "QPushButton:hover { background-color: #2980b9; }"
            )
            guide_btn.clicked.connect(open_vigem_guide)
            driver_layout.addRow("", guide_btn)

        driver_group.setLayout(driver_layout)
        layout.addWidget(driver_group)

        # Info
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "The <b>ViGEmBus</b> driver is required for virtual gamepad "
            "emulation (Xbox 360 / DualShock 4 controllers).<br><br>"
            "Without it, all other features work normally — only gamepad "
            "input from the mobile app will be unavailable.<br><br>"
            "Download it from the official "
            "<a href='https://github.com/nefarius/ViGEmBus/releases/latest'>"
            "ViGEmBus releases page</a>."
        )
        info_label.setWordWrap(True)
        info_label.setOpenExternalLinks(True)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
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
        
        # Populate certificate information
        self._load_cert_info()
    
    def _load_cert_info(self):
        """Read the server certificate and display its info."""
        try:
            from utils.paths import get_certs_dir
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes

            cert_path = get_certs_dir() / 'server.crt'
            if not cert_path.exists():
                self.cert_info_label.setText(
                    "No certificate found.\nClick 'Regenerate Certificate' to create one."
                )
                return

            cert_data = cert_path.read_bytes()
            cert = x509.load_pem_x509_certificate(cert_data)

            fingerprint = cert.fingerprint(hashes.SHA256()).hex()
            fp_fmt = ':'.join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2))

            subject = cert.subject.rfc4514_string()
            not_before = cert.not_valid_before_utc.strftime('%Y-%m-%d')
            not_after = cert.not_valid_after_utc.strftime('%Y-%m-%d')

            info_text = (
                f"Subject: {subject}\n"
                f"Valid: {not_before} \u2192 {not_after}\n"
                f"SHA-256: {fp_fmt[:47]}..."
            )
            self.cert_info_label.setText(info_text)
            self.cert_info_label.setWordWrap(True)
        except Exception as e:
            logger.warning(f"Could not load certificate info: {e}")
            self.cert_info_label.setText(f"Error reading certificate: {e}")
    
    def load_trusted_devices(self):
        """Load list of trusted devices from the authenticator."""
        self.devices_list.clear()
        
        if not self.authenticator:
            return
        
        import time as _time
        for device_id, info in self.authenticator.trusted_devices.items():
            name = info.get('name', 'Unknown')
            first_ts = info.get('first_connected')
            last_ts = info.get('last_connected')
            
            first_str = _time.strftime('%Y-%m-%d %H:%M', _time.localtime(first_ts)) if first_ts else '?'
            last_str = _time.strftime('%Y-%m-%d %H:%M', _time.localtime(last_ts)) if last_ts else '?'
            
            label = f"{name}  |  ID: {device_id[:12]}…  |  First: {first_str}  |  Last: {last_str}"
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, device_id)
            self.devices_list.addItem(item)
    
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
        if current_item and self.authenticator:
            device_id = current_item.data(Qt.ItemDataRole.UserRole)
            if device_id:
                self.authenticator.remove_trusted_device(device_id)
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
            if self.authenticator:
                for did in list(self.authenticator.trusted_devices.keys()):
                    self.authenticator.remove_trusted_device(did)
    
    def _configure_firewall(self):
        """Request firewall configuration via UAC."""
        from security.firewall_config import configure_firewall
        _profiles = ['private', 'public', 'all']
        profile = _profiles[self.firewall_profile_combo.currentIndex()]
        result = configure_firewall(profile=profile)
        if result["success"]:
            self.config.set('firewall_configured', True)
            self.config.set('firewall_profile', profile)
            self.config.save()
            QMessageBox.information(self, "Firewall", result["message"])
        else:
            QMessageBox.warning(
                self, "Firewall",
                f"Could not configure firewall:\n{result['message']}\n\n"
                "You may need to allow the ports manually.",
            )
    
    def _show_terms(self):
        """Show Terms & Privacy Policy in read-only mode."""
        from ui.terms_dialog import TermsDialog
        dlg = TermsDialog(self, read_only=True)
        dlg.exec()