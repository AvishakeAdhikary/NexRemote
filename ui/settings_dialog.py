from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Server port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Server Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(self.config.get('server_port', 8888))
        port_layout.addWidget(self.port_spin)
        layout.addLayout(port_layout)
        
        # Screen quality
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Screen Quality (1-100):"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(self.config.get('screen_quality', 75))
        quality_layout.addWidget(self.quality_spin)
        layout.addLayout(quality_layout)
        
        # Mouse sensitivity
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(QLabel("Mouse Sensitivity:"))
        self.sens_spin = QDoubleSpinBox()
        self.sens_spin.setRange(0.1, 5.0)
        self.sens_spin.setSingleStep(0.1)
        self.sens_spin.setValue(self.config.get('mouse_sensitivity', 1.0))
        sens_layout.addWidget(self.sens_spin)
        layout.addLayout(sens_layout)
        
        # Enable gamepad
        self.gamepad_check = QCheckBox("Enable Virtual Gamepad")
        self.gamepad_check.setChecked(self.config.get('enable_gamepad', True))
        layout.addWidget(self.gamepad_check)
        
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def accept(self):
        """Save settings on accept"""
        self.config.set('server_port', self.port_spin.value())
        self.config.set('screen_quality', self.quality_spin.value())
        self.config.set('mouse_sensitivity', self.sens_spin.value())
        self.config.set('enable_gamepad', self.gamepad_check.isChecked())
        super().accept()