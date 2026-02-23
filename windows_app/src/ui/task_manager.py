"""
Task Manager
Manage Windows processes from mobile device
"""
import psutil
from utils.logger import get_logger

logger = get_logger(__name__)

class TaskManager:
    """Windows process manager"""
    
    def __init__(self):
        logger.info("Task manager initialized")
    
    def handle_request(self, data: dict) -> dict:
        """Handle task manager requests"""
        try:
            action = data.get('action')
            
            if action == 'list_processes':
                return self._list_processes()
            elif action == 'end_process':
                return self._end_process(data.get('pid'))
            elif action == 'system_info':
                return self._get_system_info()
            else:
                return {'type': 'task_manager', 'action': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error handling task manager request: {e}", exc_info=True)
            return {'type': 'task_manager', 'action': 'error', 'message': str(e)}
    
    def _list_processes(self) -> dict:
        """List all running processes"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    info = proc.info
                    memory = info.get('memory_info')
                    
                    process_data = {
                        'pid': info['pid'],
                        'name': info['name'],
                        'cpu': round(info.get('cpu_percent', 0), 1),
                        'memory': memory.rss if memory else 0,
                    }
                    
                    processes.append(process_data)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Sort by CPU usage (descending)
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            
            return {
                'type': 'task_manager',
                'action': 'list_processes',
                'processes': processes
            }
            
        except Exception as e:
            logger.error(f"Error listing processes: {e}")
            return {'type': 'task_manager', 'action': 'error', 'message': f'Failed to list processes: {str(e)}'}
    
    def _end_process(self, pid: int) -> dict:
        """Terminate a process by PID, retrying with UAC if access is denied."""
        try:
            process = psutil.Process(pid)
            name = process.name()
            
            # Attempt normal (non-elevated) termination first
            process.terminate()
            
            # Wait up to 3 seconds for graceful termination
            try:
                process.wait(timeout=3)
            except psutil.TimeoutExpired:
                # Force kill if not terminated
                process.kill()
            
            logger.info(f"Terminated process: {name} (PID: {pid})")
            
            return {
                'type': 'task_manager',
                'action': 'process_ended',
                'pid': pid,
                'name': name
            }
            
        except psutil.NoSuchProcess:
            return {'type': 'task_manager', 'action': 'error', 'message': 'Process not found'}
        except psutil.AccessDenied:
            # Need elevation — request UAC to kill this process
            logger.info(f"Access denied for PID {pid}, requesting elevation...")
            return self._end_process_elevated(pid)
        except Exception as e:
            logger.error(f"Error ending process: {e}")
            return {'type': 'task_manager', 'action': 'error', 'message': f'Failed to end process: {str(e)}'}
    
    def _end_process_elevated(self, pid: int) -> dict:
        """Retry process termination via UAC elevation."""
        try:
            from utils.elevate import run_elevated
            result = run_elevated("--kill-pid", str(pid))
            
            if result["success"]:
                logger.info(f"Elevated kill succeeded for PID {pid}")
                return {
                    'type': 'task_manager',
                    'action': 'process_ended',
                    'pid': pid,
                    'name': result.get('message', ''),
                    'elevated': True,
                }
            else:
                logger.warning(f"Elevated kill failed for PID {pid}: {result['message']}")
                return {
                    'type': 'task_manager',
                    'action': 'error',
                    'message': f"Elevation required — {result['message']}",
                    'elevation_required': True,
                }
        except Exception as e:
            logger.error(f"Error during elevated process kill: {e}")
            return {
                'type': 'task_manager',
                'action': 'error',
                'message': f'Failed to terminate process (elevation failed): {str(e)}',
                'elevation_required': True,
            }

    
    def _get_system_info(self) -> dict:
        """Get system resource information"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('C:\\')
            
            return {
                'type': 'task_manager',
                'action': 'system_info',
                'cpu_usage': round(cpu_percent, 1),
                'memory_usage': round(memory.percent, 1),
                'disk_usage': round(disk.percent, 1),
                'memory_total': memory.total,
                'memory_available': memory.available,
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {'type': 'task_manager', 'action': 'error', 'message': f'Failed to get system info: {str(e)}'}
