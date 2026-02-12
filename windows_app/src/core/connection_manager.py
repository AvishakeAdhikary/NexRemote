"""
Connection Manager
Handles client connections and approval requests
"""
import asyncio
from typing import Dict
from PyQt6.QtCore import QObject, pyqtSignal
from utils.logger import get_logger

logger = get_logger(__name__)

class ConnectionManager(QObject):
    """Manage client connections and approvals"""
    
    approval_requested = pyqtSignal(str, str, object)  # device_id, device_name, future
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.pending_approvals: Dict[str, asyncio.Future] = {}
    
    async def request_approval(self, device_id: str, device_name: str) -> bool:
        """Request approval for new connection"""
        if not self.config.get('require_approval', True):
            logger.info(f"Auto-approving connection from {device_name} (approval disabled)")
            return True
        
        logger.info(f"Requesting approval for {device_name} ({device_id})")
        
        # Create approval future
        future = asyncio.Future()
        self.pending_approvals[device_id] = future
        
        # Emit signal for UI (pass the future so UI can set result)
        self.approval_requested.emit(device_id, device_name, future)
        
        # Wait for approval (with timeout)
        try:
            approved = await asyncio.wait_for(future, timeout=60.0)
            logger.info(f"Connection {'approved' if approved else 'rejected'} for {device_name}")
            return approved
        except asyncio.TimeoutError:
            logger.warning(f"Approval timeout for {device_name}")
            return False
        finally:
            if device_id in self.pending_approvals:
                del self.pending_approvals[device_id]
    
    def approve_connection(self, device_id: str):
        """Approve pending connection"""
        if device_id in self.pending_approvals:
            if not self.pending_approvals[device_id].done():
                self.pending_approvals[device_id].set_result(True)
                logger.info(f"Approved connection for device {device_id}")
    
    def reject_connection(self, device_id: str):
        """Reject pending connection"""
        if device_id in self.pending_approvals:
            if not self.pending_approvals[device_id].done():
                self.pending_approvals[device_id].set_result(False)
                logger.info(f"Rejected connection for device {device_id}")