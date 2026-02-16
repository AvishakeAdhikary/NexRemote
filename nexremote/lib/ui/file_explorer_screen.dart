import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/file_explorer_controller.dart';

class FileExplorerScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const FileExplorerScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<FileExplorerScreen> createState() => _FileExplorerScreenState();
}

class _FileExplorerScreenState extends State<FileExplorerScreen> {
  late FileExplorerController _controller;
  String _currentPath = 'C:\\';
  List<Map<String, dynamic>> _files = [];
  List<String> _pathHistory = ['C:\\'];
  bool _isLoading = false;
  final TextEditingController _searchController = TextEditingController();

  // Clipboard for copy/paste
  String? _clipboardPath;
  bool _clipboardIsCut = false;

  @override
  void initState() {
    super.initState();
    _controller = FileExplorerController(widget.connectionManager);
    _controller.responseStream.listen(_handleResponse);
    _loadDirectory(_currentPath);
  }

  void _handleResponse(Map<String, dynamic> data) {
    final action = data['action'];

    if (action == 'list' || action == 'search') {
      setState(() {
        _files = List<Map<String, dynamic>>.from(data['files'] ?? []);
        _isLoading = false;
      });
    } else if (action == 'file_content') {
      // Open text editor with file content
      _openTextEditor(data['path'], data['name'], data['content'] ?? '');
    } else if (action == 'file_saved') {
      _showSuccess('File saved: ${data['name']}');
    } else if (action == 'folder_created' || action == 'file_created') {
      _showSuccess('Created: ${data['name']}');
      _loadDirectory(_currentPath);
    } else if (action == 'renamed') {
      _showSuccess('Renamed to: ${data['new_name']}');
      _loadDirectory(_currentPath);
    } else if (action == 'deleted') {
      _showSuccess('Deleted: ${data['name']}');
      _loadDirectory(_currentPath);
    } else if (action == 'copied') {
      _showSuccess('Copied successfully');
      _loadDirectory(_currentPath);
    } else if (action == 'moved') {
      _showSuccess('Moved successfully');
      _clipboardPath = null;
      _clipboardIsCut = false;
      _loadDirectory(_currentPath);
    } else if (action == 'file_opened' || action == 'folder_opened') {
      _showSuccess('Opened: ${data['path']}');
    } else if (action == 'properties') {
      _showPropertiesDialog(data);
    } else if (action == 'error') {
      _showError(data['message'] ?? 'An error occurred');
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _loadDirectory(String path) {
    setState(() {
      _isLoading = true;
      _currentPath = path;
    });
    _controller.requestDirectoryList(path);
    _searchController.clear();
  }

  void _navigateToPath(String path) {
    _pathHistory.add(path);
    _loadDirectory(path);
  }

  void _navigateBack() {
    if (_pathHistory.length > 1) {
      _pathHistory.removeLast();
      _loadDirectory(_pathHistory.last);
    }
  }

  void _navigateToBreadcrumb(int index) {
    if (index < _pathHistory.length - 1) {
      _pathHistory.removeRange(index + 1, _pathHistory.length);
      _loadDirectory(_pathHistory.last);
    }
  }

  void _onItemTap(Map<String, dynamic> item) {
    if (item['is_directory'] == true) {
      _navigateToPath(item['path']);
    } else {
      _showFileOptions(item);
    }
  }

  void _onItemLongPress(Map<String, dynamic> item) {
    _showContextMenu(item);
  }

  // --- Context Menu ---

  void _showContextMenu(Map<String, dynamic> item) {
    final isDir = item['is_directory'] == true;

    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF2A2A2A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                item['name'] ?? '',
                style: const TextStyle(
                    fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (!isDir)
              _contextMenuItem(Icons.open_in_new, 'Open on PC', () {
                Navigator.pop(context);
                _controller.openFile(item['path']);
              }),
            if (!isDir)
              _contextMenuItem(Icons.edit_document, 'Edit', () {
                Navigator.pop(context);
                _controller.readFile(item['path']);
              }),
            _contextMenuItem(Icons.drive_file_rename_outline, 'Rename', () {
              Navigator.pop(context);
              _showRenameDialog(item);
            }),
            _contextMenuItem(Icons.copy, 'Copy', () {
              Navigator.pop(context);
              setState(() {
                _clipboardPath = item['path'];
                _clipboardIsCut = false;
              });
              _showSuccess('Copied to clipboard: ${item['name']}');
            }),
            _contextMenuItem(Icons.cut, 'Cut', () {
              Navigator.pop(context);
              setState(() {
                _clipboardPath = item['path'];
                _clipboardIsCut = true;
              });
              _showSuccess('Cut: ${item['name']}');
            }),
            _contextMenuItem(Icons.content_copy, 'Copy Path', () {
              Navigator.pop(context);
              Clipboard.setData(ClipboardData(text: item['path']));
              _showSuccess('Path copied');
            }),
            _contextMenuItem(Icons.info_outline, 'Properties', () {
              Navigator.pop(context);
              _controller.getFileProperties(item['path']);
            }),
            _contextMenuItem(Icons.delete_outline, 'Delete', () {
              Navigator.pop(context);
              _confirmDelete(item);
            }, color: Colors.red),
          ],
        ),
      ),
    );
  }

  Widget _contextMenuItem(IconData icon, String label, VoidCallback onTap,
      {Color color = Colors.white}) {
    return ListTile(
      leading: Icon(icon, color: color, size: 22),
      title: Text(label, style: TextStyle(color: color)),
      dense: true,
      onTap: onTap,
    );
  }

  // --- CRUD Dialogs ---

  void _showCreateDialog() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF2A2A2A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Create New',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white)),
            const SizedBox(height: 16),
            _contextMenuItem(Icons.create_new_folder, 'New Folder', () {
              Navigator.pop(context);
              _showNameInputDialog('Create Folder', (name) {
                _controller.createFolder(_currentPath, name);
              });
            }),
            _contextMenuItem(Icons.note_add, 'New File', () {
              Navigator.pop(context);
              _showNameInputDialog('Create File', (name) {
                _controller.createFile(_currentPath, name);
              });
            }),
          ],
        ),
      ),
    );
  }

  void _showNameInputDialog(String title, Function(String) onSubmit) {
    final nameController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF2A2A2A),
        title: Text(title, style: const TextStyle(color: Colors.white)),
        content: TextField(
          controller: nameController,
          autofocus: true,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: 'Enter name...',
            hintStyle: TextStyle(color: Colors.grey[500]),
            enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(color: Colors.grey[700]!),
            ),
            focusedBorder: const OutlineInputBorder(
              borderSide: BorderSide(color: Colors.blue),
            ),
          ),
          onSubmitted: (value) {
            if (value.trim().isNotEmpty) {
              Navigator.pop(context);
              onSubmit(value.trim());
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              final name = nameController.text.trim();
              if (name.isNotEmpty) {
                Navigator.pop(context);
                onSubmit(name);
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  void _showRenameDialog(Map<String, dynamic> item) {
    final nameController = TextEditingController(text: item['name']);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF2A2A2A),
        title: const Text('Rename', style: TextStyle(color: Colors.white)),
        content: TextField(
          controller: nameController,
          autofocus: true,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: 'Enter new name...',
            hintStyle: TextStyle(color: Colors.grey[500]),
            enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(color: Colors.grey[700]!),
            ),
            focusedBorder: const OutlineInputBorder(
              borderSide: BorderSide(color: Colors.blue),
            ),
          ),
          onSubmitted: (value) {
            if (value.trim().isNotEmpty) {
              Navigator.pop(context);
              _controller.renameItem(item['path'], value.trim());
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              final name = nameController.text.trim();
              if (name.isNotEmpty) {
                Navigator.pop(context);
                _controller.renameItem(item['path'], name);
              }
            },
            child: const Text('Rename'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(Map<String, dynamic> item) {
    final isDir = item['is_directory'] == true;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF2A2A2A),
        title: const Text('Delete', style: TextStyle(color: Colors.white)),
        content: Text(
          'Are you sure you want to delete "${item['name']}"?${isDir ? '\n\nThis will delete the folder and ALL its contents.' : ''}',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _controller.deleteItem(item['path']);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  void _pasteClipboard() {
    if (_clipboardPath == null) return;

    if (_clipboardIsCut) {
      _controller.moveItem(_clipboardPath!, _currentPath);
    } else {
      _controller.copyItem(_clipboardPath!, _currentPath);
    }
  }

  // --- Properties Dialog ---

  void _showPropertiesDialog(Map<String, dynamic> data) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF2A2A2A),
        title: Text(data['name'] ?? 'Properties',
            style: const TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _propertyRow('Type', data['is_directory'] == true ? 'Folder' : 'File'),
            _propertyRow('Size', _formatFileSize(data['size'])),
            _propertyRow('Created', data['created'] ?? ''),
            _propertyRow('Modified', data['modified'] ?? ''),
            _propertyRow('Accessed', data['accessed'] ?? ''),
            _propertyRow('Path', data['path'] ?? ''),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _propertyRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(label,
                style: TextStyle(
                    color: Colors.grey[400], fontWeight: FontWeight.w600)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(color: Colors.white70)),
          ),
        ],
      ),
    );
  }

  // --- Text Editor ---

  void _openTextEditor(String path, String name, String content) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => _TextEditorScreen(
          path: path,
          name: name,
          initialContent: content,
          onSave: (newContent) {
            _controller.writeFile(path, newContent);
          },
        ),
      ),
    );
  }

  void _showFileOptions(Map<String, dynamic> file) {
    _showContextMenu(file);
  }

  void _performSearch() {
    final query = _searchController.text.trim();
    if (query.isEmpty) {
      _loadDirectory(_currentPath);
    } else {
      setState(() {
        _isLoading = true;
      });
      _controller.searchFiles(_currentPath, query);
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  void _showSuccess(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.green),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('File Explorer'),
        actions: [
          if (_clipboardPath != null)
            IconButton(
              icon: const Icon(Icons.paste, color: Colors.amber),
              onPressed: _pasteClipboard,
              tooltip: 'Paste here',
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _loadDirectory(_currentPath),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateDialog,
        backgroundColor: Colors.blue,
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          // Search bar
          _buildSearchBar(),

          // Breadcrumb navigation
          _buildBreadcrumbs(),

          // File list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _buildFileList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        border: Border(
          bottom: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: TextField(
        controller: _searchController,
        decoration: InputDecoration(
          hintText: 'Search files...',
          prefixIcon: const Icon(Icons.search),
          suffixIcon: _searchController.text.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    _searchController.clear();
                    _loadDirectory(_currentPath);
                  },
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          contentPadding: const EdgeInsets.symmetric(vertical: 8),
        ),
        onSubmitted: (_) => _performSearch(),
        onChanged: (value) => setState(() {}),
      ),
    );
  }

  Widget _buildBreadcrumbs() {
    return Container(
      height: 50,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Colors.grey[850],
        border: Border(
          bottom: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: Row(
        children: [
          if (_pathHistory.length > 1)
            IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: _navigateBack,
            ),
          Expanded(
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: _pathHistory.length,
              itemBuilder: (context, index) {
                final parts = _pathHistory[index].split('\\');
                final displayName = index == 0 ? parts.first : parts.last;
                final isLast = index == _pathHistory.length - 1;

                return Row(
                  children: [
                    if (index > 0) const Icon(Icons.chevron_right, size: 16),
                    TextButton(
                      onPressed: () => _navigateToBreadcrumb(index),
                      child: Text(
                        displayName,
                        style: TextStyle(
                          color: isLast ? Colors.blue : Colors.grey[400],
                          fontWeight: isLast ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFileList() {
    if (_files.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.folder_open, size: 100, color: Colors.grey[600]),
            const SizedBox(height: 16),
            Text(
              'Empty folder',
              style: TextStyle(fontSize: 18, color: Colors.grey[400]),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async => _loadDirectory(_currentPath),
      child: ListView.builder(
        itemCount: _files.length,
        itemBuilder: (context, index) {
          final item = _files[index];
          final isDirectory = item['is_directory'] == true;
          final name = item['name'] ?? 'Unknown';
          final size = item['size'];
          final modified = item['modified'];

          return ListTile(
            leading: Icon(
              isDirectory ? Icons.folder : _getFileIcon(name),
              color: isDirectory ? Colors.amber : Colors.blue,
              size: 32,
            ),
            title: Text(
              name,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
            subtitle: Text(
              isDirectory
                  ? 'Folder • ${modified ?? ''}'
                  : '${_formatFileSize(size)} • ${modified ?? ''}',
              style: TextStyle(color: Colors.grey[500], fontSize: 12),
            ),
            trailing: Icon(
              isDirectory ? Icons.chevron_right : Icons.more_vert,
              color: Colors.grey[600],
            ),
            onTap: () => _onItemTap(item),
            onLongPress: () => _onItemLongPress(item),
          );
        },
      ),
    );
  }

  IconData _getFileIcon(String name) {
    final ext = name.contains('.') ? name.split('.').last.toLowerCase() : '';
    switch (ext) {
      case 'txt': case 'md': case 'log':
        return Icons.description;
      case 'py': case 'dart': case 'js': case 'ts': case 'java': case 'cpp': case 'c': case 'h': case 'cs':
        return Icons.code;
      case 'json': case 'xml': case 'yaml': case 'yml': case 'toml':
        return Icons.data_object;
      case 'jpg': case 'jpeg': case 'png': case 'gif': case 'bmp': case 'svg': case 'webp':
        return Icons.image;
      case 'mp4': case 'avi': case 'mkv': case 'mov': case 'wmv':
        return Icons.video_file;
      case 'mp3': case 'wav': case 'flac': case 'aac': case 'ogg':
        return Icons.audio_file;
      case 'pdf':
        return Icons.picture_as_pdf;
      case 'zip': case 'rar': case '7z': case 'tar': case 'gz':
        return Icons.archive;
      case 'exe': case 'msi':
        return Icons.launch;
      case 'dll': case 'sys':
        return Icons.settings_applications;
      default:
        return Icons.insert_drive_file;
    }
  }

  String _formatFileSize(dynamic bytes) {
    if (bytes == null) return '';
    final size = bytes is int ? bytes : int.tryParse(bytes.toString()) ?? 0;
    if (size < 1024) return '$size B';
    if (size < 1048576) return '${(size / 1024).toStringAsFixed(1)} KB';
    if (size < 1073741824) return '${(size / 1048576).toStringAsFixed(1)} MB';
    return '${(size / 1073741824).toStringAsFixed(1)} GB';
  }

  @override
  void dispose() {
    _controller.dispose();
    _searchController.dispose();
    super.dispose();
  }
}

// --- Built-in Text Editor Screen ---

class _TextEditorScreen extends StatefulWidget {
  final String path;
  final String name;
  final String initialContent;
  final Function(String) onSave;

  const _TextEditorScreen({
    required this.path,
    required this.name,
    required this.initialContent,
    required this.onSave,
  });

  @override
  State<_TextEditorScreen> createState() => _TextEditorScreenState();
}

class _TextEditorScreenState extends State<_TextEditorScreen> {
  late TextEditingController _textController;
  bool _hasChanges = false;
  bool _wordWrap = true;

  @override
  void initState() {
    super.initState();
    _textController = TextEditingController(text: widget.initialContent);
    _textController.addListener(() {
      if (!_hasChanges && _textController.text != widget.initialContent) {
        setState(() => _hasChanges = true);
      }
    });
  }

  void _save() {
    widget.onSave(_textController.text);
    setState(() => _hasChanges = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('File saved'), backgroundColor: Colors.green),
    );
  }

  Future<bool> _onWillPop() async {
    if (!_hasChanges) return true;

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF2A2A2A),
        title: const Text('Unsaved Changes', style: TextStyle(color: Colors.white)),
        content: const Text('Save before closing?',
            style: TextStyle(color: Colors.white70)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Discard', style: TextStyle(color: Colors.red)),
          ),
          TextButton(
            onPressed: () {
              _save();
              Navigator.pop(context, true);
            },
            child: const Text('Save & Close'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );

    return result ?? false;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_hasChanges,
      onPopInvokedWithResult: (didPop, result) async {
        if (!didPop) {
          final shouldPop = await _onWillPop();
          if (shouldPop && context.mounted) {
            Navigator.of(context).pop();
          }
        }
      },
      child: Scaffold(
        backgroundColor: const Color(0xFF1E1E1E),
        appBar: AppBar(
          title: Row(
            children: [
              const Icon(Icons.edit_document, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  widget.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (_hasChanges)
                Container(
                  margin: const EdgeInsets.only(left: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.orange,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text('Modified',
                      style: TextStyle(fontSize: 10, color: Colors.white)),
                ),
            ],
          ),
          actions: [
            IconButton(
              icon: Icon(_wordWrap ? Icons.wrap_text : Icons.format_align_left,
                  color: _wordWrap ? Colors.blue : Colors.grey),
              onPressed: () => setState(() => _wordWrap = !_wordWrap),
              tooltip: 'Word Wrap',
            ),
            IconButton(
              icon: Icon(Icons.save,
                  color: _hasChanges ? Colors.blue : Colors.grey),
              onPressed: _hasChanges ? _save : null,
              tooltip: 'Save',
            ),
          ],
        ),
        body: Padding(
          padding: const EdgeInsets.all(8),
          child: TextField(
            controller: _textController,
            maxLines: null,
            expands: true,
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 14,
              color: Colors.white,
              height: 1.5,
            ),
            decoration: const InputDecoration(
              border: InputBorder.none,
              contentPadding: EdgeInsets.all(8),
            ),
            keyboardType: TextInputType.multiline,
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }
}
