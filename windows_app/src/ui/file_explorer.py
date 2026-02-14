"""
File Explorer Handler
Allows mobile client to browse Windows file system
"""
import os
import subprocess
from pathlib import Path
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class FileExplorer:
    """File system explorer for remote access"""
    
    def __init__(self, config):
        self.config = config
        # Security: whitelist of allowed root paths
        self.allowed_roots = [
            'C:\\',
            os.path.expanduser('~'),  # User home directory
        ]
        logger.info("File explorer initialized")
    
    def handle_request(self, data: dict) -> dict:
        """Handle file explorer requests"""
        try:
            action = data.get('action')
            
            if action == 'list':
                return self._list_directory(data.get('path', 'C:\\'))
            elif action == 'open':
                return self._open_file(data.get('path'))
            elif action == 'properties':
                return self._get_properties(data.get('path'))
            elif action == 'search':
                return self._search_files(data.get('path'), data.get('query'))
            elif action == 'copy_path':
                return self._copy_path(data.get('path'))
            else:
                return {'action': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error handling file explorer request: {e}", exc_info=True)
            return {'action': 'error', 'message': str(e)}
    
    def _validate_path(self, path: str) -> bool:
        """Validate path to prevent directory traversal attacks"""
        try:
            resolved = os.path.abspath(path)
            
            # Check if path is within allowed roots
            for root in self.allowed_roots:
                if resolved.startswith(os.path.abspath(root)):
                    return True
            
            logger.warning(f"Path validation failed: {path}")
            return False
        except Exception as e:
            logger.error(f"Error validating path: {e}")
            return False
    
    def _list_directory(self, path: str) -> dict:
        """List directory contents"""
        if not self._validate_path(path):
            return {'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            items = []
            
            for entry in os.scandir(path):
                try:
                    stat = entry.stat()
                    
                    item = {
                        'name': entry.name,
                        'path': entry.path,
                        'is_directory': entry.is_dir(),
                        'size': stat.st_size if entry.is_file() else None,
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                    }
                    
                    items.append(item)
                except (PermissionError, OSError) as e:
                    # Skip files/folders we can't access
                    logger.debug(f"Skipping inaccessible item: {entry.path} - {e}")
                    continue
            
            # Sort: directories first, then by name
            items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
            
            return {
                'action': 'list',
                'path': path,
                'files': items
            }
            
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            return {'action': 'error', 'message': f'Failed to list directory: {str(e)}'}
    
    def _open_file(self, path: str) -> dict:
        """Open file with default application"""
        if not self._validate_path(path):
            return {'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            if os.path.isfile(path):
                # Open file with default application
                os.startfile(path)
                logger.info(f"Opened file: {path}")
                return {'action': 'file_opened', 'path': path}
            elif os.path.isdir(path):
                # Open folder in Explorer
                subprocess.Popen(f'explorer "{path}"')
                logger.info(f"Opened folder: {path}")
                return {'action': 'folder_opened', 'path': path}
            else:
                return {'action': 'error', 'message': 'File or folder not found'}
                
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            return {'action': 'error', 'message': f'Failed to open: {str(e)}'}
    
    def _get_properties(self, path: str) -> dict:
        """Get file/folder properties"""
        if not self._validate_path(path):
            return {'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            stat = os.stat(path)
            
            properties = {
                'action': 'properties',
                'path': path,
                'name': os.path.basename(path),
                'is_directory': os.path.isdir(path),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'accessed': datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return properties
            
        except Exception as e:
            logger.error(f"Error getting properties: {e}")
            return {'action': 'error', 'message': f'Failed to get properties: {str(e)}'}
    
    def _search_files(self, path: str, query: str) -> dict:
        """Search for files matching query"""
        if not self._validate_path(path):
            return {'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            items = []
            query_lower = query.lower()
            
            # Search in current directory only (not recursive for performance)
            for entry in os.scandir(path):
                try:
                    if query_lower in entry.name.lower():
                        stat = entry.stat()
                        
                        item = {
                            'name': entry.name,
                            'path': entry.path,
                            'is_directory': entry.is_dir(),
                            'size': stat.st_size if entry.is_file() else None,
                            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        }
                        
                        items.append(item)
                except (PermissionError, OSError):
                    continue
            
            items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
            
            return {
                'action': 'search',
                'path': path,
                'query': query,
                'files': items
            }
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return {'action': 'error', 'message': f'Search failed: {str(e)}'}
    
    def _copy_path(self, path: str) -> dict:
        """Acknowledge path copy (actual copying happens on mobile side)"""
        return {
            'action': 'path_copied',
            'path': path
        }
