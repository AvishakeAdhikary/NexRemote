import 'package:flutter/material.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/task_manager_controller.dart';

class TaskManagerScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const TaskManagerScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<TaskManagerScreen> createState() => _TaskManagerScreenState();
}

class _TaskManagerScreenState extends State<TaskManagerScreen> {
  late TaskManagerController _controller;
  List<Map<String, dynamic>> _processes = [];
  Map<String, dynamic> _systemInfo = {};
  bool _isLoading = false;
  Timer? _refreshTimer;
  Timer? _loadingTimeoutTimer;
  String _sortBy = 'name';
  bool _sortAscending = true;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _controller = TaskManagerController(widget.connectionManager);
    _controller.responseStream.listen(_handleResponse);
    
    _loadProcessList();
    
    // Auto-refresh every 2 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      _loadProcessList();
    });
  }

  void _handleResponse(Map<String, dynamic> data) {
    if (data['action'] == 'list_processes') {
      setState(() {
        _processes = List<Map<String, dynamic>>.from(data['processes'] ?? []);
        _isLoading = false;
        _sortProcesses();
      });
    } else if (data['action'] == 'system_info') {
      setState(() {
        _systemInfo = data;
      });
    } else if (data['action'] == 'process_ended') {
      _showSuccess('Process terminated successfully');
      _loadProcessList();
    } else if (data['action'] == 'error') {
      _showError(data['message'] ?? 'An error occurred');
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _loadProcessList() {
    setState(() {
      _isLoading = true;
    });
    _controller.requestProcessList();
    _controller.requestSystemInfo();

    // Clear loading state after 5s if no response
    _loadingTimeoutTimer?.cancel();
    _loadingTimeoutTimer = Timer(const Duration(seconds: 5), () {
      if (mounted && _isLoading) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Server took too long to respond'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    });
  }

  void _sortProcesses() {
    _processes.sort((a, b) {
      int comparison = 0;
      
      switch (_sortBy) {
        case 'name':
          comparison = (a['name'] ?? '').toString().toLowerCase()
              .compareTo((b['name'] ?? '').toString().toLowerCase());
          break;
        case 'cpu':
          final aCpu = double.tryParse(a['cpu']?.toString() ?? '0') ?? 0;
          final bCpu = double.tryParse(b['cpu']?.toString() ?? '0') ?? 0;
          comparison = aCpu.compareTo(bCpu);
          break;
        case 'memory':
          final aMem = int.tryParse(a['memory']?.toString() ?? '0') ?? 0;
          final bMem = int.tryParse(b['memory']?.toString() ?? '0') ?? 0;
          comparison = aMem.compareTo(bMem);
          break;
      }
      
      return _sortAscending ? comparison : -comparison;
    });
  }

  void _setSortBy(String sortBy) {
    setState(() {
      if (_sortBy == sortBy) {
        _sortAscending = !_sortAscending;
      } else {
        _sortBy = sortBy;
        _sortAscending = false; // Default to descending for CPU and memory
      }
      _sortProcesses();
    });
  }

  void _confirmEndProcess(Map<String, dynamic> process) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('End Process'),
        content: Text(
          'Are you sure you want to end "${process['name']}"?\n\nPID: ${process['pid']}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _controller.endProcess(process['pid']);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('End Process'),
          ),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> get _filteredProcesses {
    if (_searchQuery.isEmpty) return _processes;
    
    return _processes.where((process) {
      final name = (process['name'] ?? '').toString().toLowerCase();
      return name.contains(_searchQuery.toLowerCase());
    }).toList();
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
        title: const Text('Task Manager'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadProcessList,
          ),
        ],
      ),
      body: Column(
        children: [
          // System info
          _buildSystemInfo(),

          // Search bar
          _buildSearchBar(),

          // Sort options
          _buildSortOptions(),

          // Process list
          Expanded(
            child: _buildProcessList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSystemInfo() {
    final cpuUsage = _systemInfo['cpu_usage'] ?? 0.0;
    final memoryUsage = _systemInfo['memory_usage'] ?? 0.0;
    final diskUsage = _systemInfo['disk_usage'] ?? 0.0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        border: Border(
          bottom: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildResourceIndicator('CPU', cpuUsage, Icons.memory, Colors.blue),
          _buildResourceIndicator('RAM', memoryUsage, Icons.storage, Colors.green),
          _buildResourceIndicator('Disk', diskUsage, Icons.disc_full, Colors.orange),
        ],
      ),
    );
  }

  Widget _buildResourceIndicator(String label, double usage, IconData icon, Color color) {
    return Column(
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 4),
            Text(label, style: const TextStyle(fontSize: 12)),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          '${usage.toStringAsFixed(1)}%',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: usage > 80 ? Colors.red : color,
          ),
        ),
      ],
    );
  }

  Widget _buildSearchBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[850],
        border: Border(
          bottom: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: TextField(
        controller: _searchController,
        decoration: InputDecoration(
          hintText: 'Search processes...',
          prefixIcon: const Icon(Icons.search),
          suffixIcon: _searchController.text.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    _searchController.clear();
                    setState(() => _searchQuery = '');
                  },
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          contentPadding: const EdgeInsets.symmetric(vertical: 8),
        ),
        onChanged: (value) {
          setState(() => _searchQuery = value);
        },
      ),
    );
  }

  Widget _buildSortOptions() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.grey[850],
        border: Border(
          bottom: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: Row(
        children: [
          const Text('Sort by: ', style: TextStyle(fontSize: 12)),
          const SizedBox(width: 8),
          _buildSortButton('Name', 'name'),
          const SizedBox(width: 8),
          _buildSortButton('CPU', 'cpu'),
          const SizedBox(width: 8),
          _buildSortButton('Memory', 'memory'),
        ],
      ),
    );
  }

  Widget _buildSortButton(String label, String value) {
    final isActive = _sortBy == value;
    
    return GestureDetector(
      onTap: () => _setSortBy(value),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isActive ? Colors.blue : Colors.grey[800],
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: isActive ? Colors.white : Colors.grey[400],
              ),
            ),
            if (isActive) ...[
              const SizedBox(width: 4),
              Icon(
                _sortAscending ? Icons.arrow_upward : Icons.arrow_downward,
                size: 12,
                color: Colors.white,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildProcessList() {
    final filteredList = _filteredProcesses;

    if (_isLoading && filteredList.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (filteredList.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 100, color: Colors.grey[600]),
            const SizedBox(height: 16),
            Text(
              'No processes found',
              style: TextStyle(fontSize: 18, color: Colors.grey[400]),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: filteredList.length,
      itemBuilder: (context, index) {
        final process = filteredList[index];
        final name = process['name'] ?? 'Unknown';
        final pid = process['pid'] ?? 0;
        final cpu = double.tryParse(process['cpu']?.toString() ?? '0') ?? 0;
        final memory = int.tryParse(process['memory']?.toString() ?? '0') ?? 0;

        return ListTile(
          leading: Icon(
            Icons.apps,
            color: cpu > 50 ? Colors.red : Colors.blue,
          ),
          title: Text(
            name,
            style: const TextStyle(fontWeight: FontWeight.w500),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          subtitle: Text(
            'PID: $pid • CPU: ${cpu.toStringAsFixed(1)}% • RAM: ${_formatMemory(memory)}',
            style: TextStyle(color: Colors.grey[500], fontSize: 12),
          ),
          trailing: IconButton(
            icon: const Icon(Icons.close, color: Colors.red),
            onPressed: () => _confirmEndProcess(process),
          ),
        );
      },
    );
  }

  String _formatMemory(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1048576) return '${(bytes / 1024).toStringAsFixed(0)} KB';
    if (bytes < 1073741824) return '${(bytes / 1048576).toStringAsFixed(0)} MB';
    return '${(bytes / 1073741824).toStringAsFixed(1)} GB';
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _loadingTimeoutTimer?.cancel();
    _controller.dispose();
    _searchController.dispose();
    super.dispose();
  }
}
