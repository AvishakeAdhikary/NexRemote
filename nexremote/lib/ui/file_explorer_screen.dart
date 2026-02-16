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

  @override
  void initState() {
    super.initState();
    _controller = FileExplorerController(widget.connectionManager);
    _controller.responseStream.listen(_handleResponse);
    _loadDirectory(_currentPath);
  }

  void _handleResponse(Map<String, dynamic> data) {
    if (data['action'] == 'list' || data['action'] == 'search') {
      setState(() {
        _files = List<Map<String, dynamic>>.from(data['files'] ?? []);
        _isLoading = false;
      });
    } else if (data['action'] == 'error') {
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

  void _showFileOptions(Map<String, dynamic> file) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.open_in_new),
              title: const Text('Open'),
              onTap: () {
                Navigator.pop(context);
                _controller.openFile(file['path']);
                _showSuccess('Opening ${file['name']}...');
              },
            ),
            ListTile(
              leading: const Icon(Icons.copy),
              title: const Text('Copy Path'),
              onTap: () {
                Navigator.pop(context);
                Clipboard.setData(ClipboardData(text: file['path']));
                _showSuccess('Path copied to clipboard');
              },
            ),
            ListTile(
              leading: const Icon(Icons.info),
              title: const Text('Properties'),
              onTap: () {
                Navigator.pop(context);
                _controller.getFileProperties(file['path']);
                _showSuccess('Requested properties for ${file['name']}');
              },
            ),
          ],
        ),
      ),
    );
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
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  void _showSuccess(String message) {
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
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _loadDirectory(_currentPath),
          ),
        ],
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
              'No files found',
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
              isDirectory ? Icons.folder : Icons.insert_drive_file,
              color: isDirectory ? Colors.amber : Colors.blue,
              size: 32,
            ),
            title: Text(
              name,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
            subtitle: Text(
              isDirectory
                  ? 'Folder'
                  : '${_formatFileSize(size)} • ${modified ?? ''}',
              style: TextStyle(color: Colors.grey[500], fontSize: 12),
            ),
            trailing: Icon(
              isDirectory ? Icons.chevron_right : Icons.more_vert,
              color: Colors.grey[600],
            ),
            onTap: () => _onItemTap(item),
          );
        },
      ),
    );
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
