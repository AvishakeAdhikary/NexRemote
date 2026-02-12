"""
Connection Approval Dialog
Shows when a new device wants to connect
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)

class ConnectionApprovalDialog(QDialog):
    """Dialog for approving/rejecting connection requests"""
    
    def __init__(self, device_id: str, device_name: str, future: asyncio.Future, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.device_name = device_name
        self.future = future
        
        self.setWindowTitle("New Connection Request")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.setup_ui()
        
        # Auto-reject after timeout
        self.timeout_seconds = 60
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("New Device Connection Request")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Device info group
        info_group = QGroupBox("Device Information")
        info_layout = QVBoxLayout()
        
        # Device name
        name_label = QLabel(f"Device Name: {self.device_name}")
        name_font = QFont()
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        info_layout.addWidget(name_label)
        
        # Device ID
        id_label = QLabel(f"Device ID: {self.device_id[:16]}...")
        id_label.setStyleSheet("color: gray;")
        info_layout.addWidget(id_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Warning message
        warning = QLabel("⚠️ Only approve if you recognize this device")
        warning.setStyleSheet("color: orange; font-weight: bold;")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        reject_btn.clicked.connect(self.reject)
        button_layout.addWidget(reject_btn)
        
        approve_btn = QPushButton("Approve")
        approve_btn.setStyleSheet("""
            QPushButton {
                background-color: #388e3c;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2e7d32;
            }
        """)
        approve_btn.clicked.connect(self.approve)
        button_layout.addWidget(approve_btn)
        
        layout.addLayout(button_layout)
        
        # Timeout label
        self.timeout_label = QLabel(f"Auto-reject in {self.timeout_seconds} seconds")
        self.timeout_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timeout_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.timeout_label)
    
    def approve(self):
        """Approve the connection"""
        logger.info(f"User approved connection from {self.device_name}")
        if not self.future.done():
            self.future.set_result(True)
        self.accept()
    
    def reject(self):
        """Reject the connection"""
        logger.info(f"User rejected connection from {self.device_name}")
        if not self.future.done():
            self.future.set_result(False)
        self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close - treat as rejection"""
        if not self.future.done():
            self.future.set_result(False)
        super().closeEvent(event)