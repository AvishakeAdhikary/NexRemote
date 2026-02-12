import 'package:flutter/material.dart';
import '../core/discovery.dart';
import '../core/connection_manager.dart';
import '../utils/config.dart';
import '../utils/logger.dart';

class ConnectionScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const ConnectionScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  final DiscoveryService _discoveryService = DiscoveryService();
  final Config _config = Config();
  
  List<ServerInfo> _servers = [];
  bool _discovering = false;
  
  @override
  void initState() {
    super.initState();
    _initConfig();
    _startDiscovery();
  }
  
  Future<void> _initConfig() async {
    await _config.init();
  }
  
  Future<void> _startDiscovery() async {
    setState(() {
      _discovering = true;
    });
    
    try {
      final servers = await _discoveryService.discoverServers();
      setState(() {
        _servers = servers;
      });
      
      if (servers.isEmpty) {
        _showMessage('No servers found. Make sure your PC is on the same network.');
      }
    } catch (e) {
      Logger.error('Discovery failed: $e');
      _showMessage('Discovery failed: $e');
    } finally {
      setState(() {
        _discovering = false;
      });
    }
  }
  
  Future<void> _connectToServer(ServerInfo server) async {
    try {
      final success = await widget.connectionManager.connect(
        server.address,
        server.port,              // Secure port (8765)
        server.portInsecure,      // Insecure port (8766) for fallback
        _config.deviceId,
        _config.deviceName,
        trySecureFirst: true,     // Always try secure first
      );

      if (success) {
        await _config.setLastServer('${server.address}:${server.port}');
        if (mounted) Navigator.pop(context, true);
      } else {
        if (mounted) _showMessage('Failed to connect to ${server.name}');
      }
    } catch (e) {
      Logger.error('Connection error: $e');
      if (mounted) _showMessage('Connection error: $e');
    }
  }
  
  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Connect to PC'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _discovering ? null : _startDiscovery,
          ),
        ],
      ),
      body: _discovering
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Searching for PCs...'),
                ],
              ),
            )
          : _servers.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.search_off, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      const Text('No PCs found'),
                      const SizedBox(height: 8),
                      const Text(
                        'Make sure your PC is on the same network',
                        style: TextStyle(color: Colors.grey),
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        onPressed: _startDiscovery,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _servers.length,
                  itemBuilder: (context, index) {
                    final server = _servers[index];
                    return Card(
                      child: ListTile(
                        leading: const Icon(Icons.computer, size: 48),
                        title: Text(server.name),
                        subtitle: Text('${server.address}:${server.port}'),
                        trailing: const Icon(Icons.arrow_forward_ios),
                        onTap: () => _connectToServer(server),
                      ),
                    );
                  },
                ),
    );
  }
}