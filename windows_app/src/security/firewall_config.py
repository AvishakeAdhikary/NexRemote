"""
Automatic Windows Firewall Configuration
Adds rules to allow server ports
"""
import subprocess
import sys
from utils.logger import get_logger

logger = get_logger(__name__)

def configure_firewall() -> bool:
    """
    Configure Windows Firewall to allow NexRemote server
    Returns True if successful, False otherwise
    """
    try:
        # Check if running as administrator
        if not is_admin():
            logger.warning("Not running as administrator. Firewall configuration may fail.")
            # Try to run anyway, may work on some systems
        
        # Rule name
        rule_name = "NexRemote Server"
        
        # Get executable path
        exe_path = sys.executable
        if hasattr(sys, 'frozen'):
            exe_path = sys.executable
        else:
            exe_path = f"{sys.executable} -m nexremote"
        
        # Remove existing rules (if any)
        try:
            subprocess.run([
                'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                f'name={rule_name}'
            ], capture_output=True, check=False)
        except:
            pass
        
        # Add inbound rule for TCP (WebSocket)
        result = subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={rule_name} (TCP)',
            'dir=in',
            'action=allow',
            'protocol=TCP',
            'localport=8765',
            'program=' + exe_path,
            'enable=yes'
        ], capture_output=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to add TCP firewall rule: {result.stderr.decode()}")
            return False
        
        # Add inbound rule for UDP (Discovery)
        result = subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={rule_name} (UDP)',
            'dir=in',
            'action=allow',
            'protocol=UDP',
            'localport=37020',
            'program=' + exe_path,
            'enable=yes'
        ], capture_output=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to add UDP firewall rule: {result.stderr.decode()}")
            return False
        
        logger.info("Firewall rules configured successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error configuring firewall: {e}")
        return False

def is_admin() -> bool:
    """Check if running with administrator privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def remove_firewall_rules():
    """Remove NexRemote firewall rules"""
    try:
        rule_name = "NexRemote Server"
        subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
            f'name={rule_name}'
        ], capture_output=True, check=False)
        logger.info("Firewall rules removed")
    except Exception as e:
        logger.error(f"Error removing firewall rules: {e}")