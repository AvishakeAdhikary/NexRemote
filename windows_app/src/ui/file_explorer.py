"""
File Explorer Handler
Allows mobile client to browse and manage Windows file system
"""
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class FileExplorer:
    """File system explorer for remote access with CRUD operations"""
    
    def __init__(self, config):
        self.config = config
        # Security: whitelist of allowed root paths
        self.allowed_roots = [
            'C:\\',
            os.path.expanduser('~'),  # User home directory
        ]
        # Max file size for reading text content (5 MB)
        self.max_read_size = 5 * 1024 * 1024
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
            elif action == 'create_folder':
                return self._create_folder(data.get('path'), data.get('name'))
            elif action == 'create_file':
                return self._create_file(data.get('path'), data.get('name'), data.get('content', ''))
            elif action == 'rename':
                return self._rename(data.get('path'), data.get('new_name'))
            elif action == 'delete':
                return self._delete(data.get('path'))
            elif action == 'read_file':
                return self._read_file(data.get('path'))
            elif action == 'write_file':
                return self._write_file(data.get('path'), data.get('content', ''))
            elif action == 'copy':
                return self._copy(data.get('source'), data.get('destination'))
            elif action == 'move':
                return self._move(data.get('source'), data.get('destination'))
            else:
                return {'type': 'file_explorer', 'action': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error handling file explorer request: {e}", exc_info=True)
            return {'type': 'file_explorer', 'action': 'error', 'message': str(e)}
    
    def _validate_path(self, path: str) -> bool:
        """Validate path to prevent directory traversal attacks"""
        try:
            if not path:
                return False
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
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
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
                    logger.debug(f"Skipping inaccessible item: {entry.path} - {e}")
                    continue
            
            # Sort: directories first, then by name
            items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
            
            return {
                'type': 'file_explorer',
                'action': 'list',
                'path': path,
                'files': items
            }
            
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to list directory: {str(e)}'}
    
    def _open_file(self, path: str) -> dict:
        """Open file with default application"""
        if not self._validate_path(path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            if os.path.isfile(path):
                os.startfile(path)
                logger.info(f"Opened file: {path}")
                return {'type': 'file_explorer', 'action': 'file_opened', 'path': path}
            elif os.path.isdir(path):
                subprocess.Popen(f'explorer "{path}"')
                logger.info(f"Opened folder: {path}")
                return {'type': 'file_explorer', 'action': 'folder_opened', 'path': path}
            else:
                return {'type': 'file_explorer', 'action': 'error', 'message': 'File or folder not found'}
                
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to open: {str(e)}'}
    
    def _get_properties(self, path: str) -> dict:
        """Get file/folder properties"""
        if not self._validate_path(path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            stat = os.stat(path)
            
            return {
                'type': 'file_explorer',
                'action': 'properties',
                'path': path,
                'name': os.path.basename(path),
                'is_directory': os.path.isdir(path),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'accessed': datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S'),
            }
            
        except Exception as e:
            logger.error(f"Error getting properties: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to get properties: {str(e)}'}
    
    def _search_files(self, path: str, query: str) -> dict:
        """Search for files matching query"""
        if not self._validate_path(path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            items = []
            query_lower = query.lower()
            
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
                'type': 'file_explorer',
                'action': 'search',
                'path': path,
                'query': query,
                'files': items
            }
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Search failed: {str(e)}'}
    
    def _copy_path(self, path: str) -> dict:
        """Acknowledge path copy"""
        return {'type': 'file_explorer', 'action': 'path_copied', 'path': path}
    
    # --- CRUD Operations ---
    
    def _create_folder(self, parent_path: str, name: str) -> dict:
        """Create a new folder"""
        if not self._validate_path(parent_path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            new_path = os.path.join(parent_path, name)
            os.makedirs(new_path, exist_ok=False)
            logger.info(f"Created folder: {new_path}")
            return {
                'type': 'file_explorer',
                'action': 'folder_created',
                'path': new_path,
                'name': name
            }
        except FileExistsError:
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Folder "{name}" already exists'}
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to create folder: {str(e)}'}
    
    def _create_file(self, parent_path: str, name: str, content: str = '') -> dict:
        """Create a new file with optional content"""
        if not self._validate_path(parent_path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            new_path = os.path.join(parent_path, name)
            if os.path.exists(new_path):
                return {'type': 'file_explorer', 'action': 'error', 'message': f'File "{name}" already exists'}
            
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Created file: {new_path}")
            return {
                'type': 'file_explorer',
                'action': 'file_created',
                'path': new_path,
                'name': name
            }
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to create file: {str(e)}'}
    
    def _rename(self, path: str, new_name: str) -> dict:
        """Rename a file or folder"""
        if not self._validate_path(path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            parent = os.path.dirname(path)
            new_path = os.path.join(parent, new_name)
            
            if os.path.exists(new_path):
                return {'type': 'file_explorer', 'action': 'error', 'message': f'"{new_name}" already exists'}
            
            os.rename(path, new_path)
            logger.info(f"Renamed: {path} -> {new_path}")
            return {
                'type': 'file_explorer',
                'action': 'renamed',
                'old_path': path,
                'new_path': new_path,
                'new_name': new_name
            }
        except Exception as e:
            logger.error(f"Error renaming: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to rename: {str(e)}'}
    
    def _delete(self, path: str) -> dict:
        """Delete a file or folder"""
        if not self._validate_path(path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            name = os.path.basename(path)
            
            if os.path.isdir(path):
                shutil.rmtree(path)
                logger.info(f"Deleted folder: {path}")
            elif os.path.isfile(path):
                os.remove(path)
                logger.info(f"Deleted file: {path}")
            else:
                return {'type': 'file_explorer', 'action': 'error', 'message': 'File or folder not found'}
            
            return {
                'type': 'file_explorer',
                'action': 'deleted',
                'path': path,
                'name': name
            }
        except PermissionError:
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Permission denied: cannot delete "{os.path.basename(path)}"'}
        except Exception as e:
            logger.error(f"Error deleting: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to delete: {str(e)}'}
    
    def _read_file(self, path: str) -> dict:
        """Read text file content"""
        if not self._validate_path(path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            if not os.path.isfile(path):
                return {'type': 'file_explorer', 'action': 'error', 'message': 'Not a file'}
            
            file_size = os.path.getsize(path)
            if file_size > self.max_read_size:
                return {'type': 'file_explorer', 'action': 'error', 'message': f'File too large ({file_size} bytes). Max: {self.max_read_size} bytes'}
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            return {
                'type': 'file_explorer',
                'action': 'file_content',
                'path': path,
                'name': os.path.basename(path),
                'content': content,
                'size': file_size
            }
        except UnicodeDecodeError:
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Cannot read binary file as text'}
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to read file: {str(e)}'}
    
    def _write_file(self, path: str, content: str) -> dict:
        """Write content to a text file"""
        if not self._validate_path(path):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Wrote file: {path} ({len(content)} chars)")
            return {
                'type': 'file_explorer',
                'action': 'file_saved',
                'path': path,
                'name': os.path.basename(path),
                'size': len(content)
            }
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to write file: {str(e)}'}
    
    def _copy(self, source: str, destination: str) -> dict:
        """Copy a file or folder"""
        if not self._validate_path(source) or not self._validate_path(destination):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            name = os.path.basename(source)
            dest_path = os.path.join(destination, name)
            
            if os.path.isdir(source):
                shutil.copytree(source, dest_path)
            else:
                shutil.copy2(source, dest_path)
            
            logger.info(f"Copied: {source} -> {dest_path}")
            return {
                'type': 'file_explorer',
                'action': 'copied',
                'source': source,
                'destination': dest_path
            }
        except Exception as e:
            logger.error(f"Error copying: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to copy: {str(e)}'}
    
    def _move(self, source: str, destination: str) -> dict:
        """Move a file or folder"""
        if not self._validate_path(source) or not self._validate_path(destination):
            return {'type': 'file_explorer', 'action': 'error', 'message': 'Invalid or restricted path'}
        
        try:
            name = os.path.basename(source)
            dest_path = os.path.join(destination, name)
            
            shutil.move(source, dest_path)
            
            logger.info(f"Moved: {source} -> {dest_path}")
            return {
                'type': 'file_explorer',
                'action': 'moved',
                'source': source,
                'destination': dest_path
            }
        except Exception as e:
            logger.error(f"Error moving: {e}")
            return {'type': 'file_explorer', 'action': 'error', 'message': f'Failed to move: {str(e)}'}
