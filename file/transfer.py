import os
import base64
import logging

logger_file = logging.getLogger(__name__)

class FileTransferHandler:
    """Handle file transfer operations"""
    
    def __init__(self):
        self.chunk_size = 1024 * 1024  # 1MB chunks
        
    def list_files(self, path=''):
        """List files in directory"""
        try:
            if not path:
                # List drives on Windows
                import string
                from ctypes import windll
                drives = []
                bitmask = windll.kernel32.GetLogicalDrives()
                for letter in string.ascii_uppercase:
                    if bitmask & 1:
                        drives.append({'name': f"{letter}:\\", 'type': 'drive', 'size': 0})
                    bitmask >>= 1
                return drives
            
            if not os.path.exists(path):
                raise Exception(f"Path does not exist: {path}")
            
            files = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    is_dir = os.path.isdir(item_path)
                    size = 0 if is_dir else os.path.getsize(item_path)
                    files.append({
                        'name': item,
                        'path': item_path,
                        'type': 'folder' if is_dir else 'file',
                        'size': size
                    })
                except:
                    continue
            
            return files
        except Exception as e:
            logger_file.error(f"List files error: {e}")
            raise
    
    def read_file(self, path):
        """Read file and return as base64"""
        try:
            with open(path, 'rb') as f:
                content = f.read()
            
            content_base64 = base64.b64encode(content).decode('utf-8')
            filename = os.path.basename(path)
            size = len(content)
            
            return {
                'filename': filename,
                'content': content_base64,
                'size': size
            }
        except Exception as e:
            logger_file.error(f"Read file error: {e}")
            raise
    
    def write_file(self, path, content_base64):
        """Write file from base64 content"""
        try:
            content = base64.b64decode(content_base64)
            
            # Create directory if needed
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(path, 'wb') as f:
                f.write(content)
            
            return True
        except Exception as e:
            logger_file.error(f"Write file error: {e}")
            raise