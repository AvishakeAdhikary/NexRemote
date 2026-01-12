import psutil
import subprocess
import logging

logger_process = logging.getLogger(__name__)

class ProcessManager:
    """Manage system processes"""
    
    def get_process_list(self):
        """Get list of running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    info = proc.info
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'cpu': info['cpu_percent'],
                        'memory': info['memory_info'].rss if info['memory_info'] else 0
                    })
                except:
                    continue
            
            return processes
        except Exception as e:
            logger_process.error(f"Get process list error: {e}")
            return []
    
    def kill_process(self, pid):
        """Kill process by PID"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=3)
            return True
        except Exception as e:
            logger_process.error(f"Kill process error: {e}")
            return False
    
    def launch_app(self, path):
        """Launch application"""
        try:
            subprocess.Popen(path, shell=True)
            return True
        except Exception as e:
            logger_process.error(f"Launch app error: {e}")
            return False