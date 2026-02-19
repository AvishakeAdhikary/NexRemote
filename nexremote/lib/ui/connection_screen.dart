import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
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
  bool _connecting = false;

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
        _showMessage('No servers found. Try scanning a QR code or check your network.');
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
    if (_connecting) return;
    setState(() => _connecting = true);

    try {
      final success = await widget.connectionManager.connect(
        server.address,
        server.port,
        server.portInsecure,
        _config.deviceId,
        _config.deviceName,
        trySecureFirst: true,
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
    } finally {
      if (mounted) setState(() => _connecting = false);
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  // ─── QR Code Scanning ──────────────────────────────────────────────

  void _openQRScanner() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => _QRScannerScreen(
          onScanned: (data) {
            Navigator.pop(context); // Close scanner
            _handleQRData(data);
          },
        ),
      ),
    );
  }

  void _handleQRData(String rawData) {
    try {
      final data = jsonDecode(rawData) as Map<String, dynamic>;

      final host = data['host'] as String?;
      final port = data['port'] as int?;
      final portInsecure = data['port_insecure'] as int?;
      final name = data['name'] as String?;
      final id = data['id'] as String?;

      if (host == null || port == null) {
        _showMessage('Invalid QR code — missing connection info');
        return;
      }

      final server = ServerInfo(
        name: name ?? 'PC',
        address: host,
        port: port,
        portInsecure: portInsecure ?? (port + 1),
        id: id ?? '',
        version: '1.0.0',
      );

      _showMessage('Connecting to ${server.name} at ${server.address}...');
      _connectToServer(server);
    } catch (e) {
      Logger.error('Failed to parse QR code: $e');
      _showMessage('Invalid QR code format');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Connect to PC'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            tooltip: 'Scan QR Code',
            onPressed: _openQRScanner,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _discovering ? null : _startDiscovery,
          ),
        ],
      ),
      body: _connecting
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Connecting...'),
                ],
              ),
            )
          : _discovering
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
                          const Text('No PCs found on network'),
                          const SizedBox(height: 8),
                          const Text(
                            'Make sure your PC is on the same network\nor scan a QR code to connect directly',
                            style: TextStyle(color: Colors.grey),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 24),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              ElevatedButton.icon(
                                onPressed: _startDiscovery,
                                icon: const Icon(Icons.refresh),
                                label: const Text('Retry'),
                              ),
                              const SizedBox(width: 16),
                              ElevatedButton.icon(
                                onPressed: _openQRScanner,
                                icon: const Icon(Icons.qr_code_scanner),
                                label: const Text('Scan QR'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.deepPurple,
                                  foregroundColor: Colors.white,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _servers.length + 1, // +1 for QR scan card
                      itemBuilder: (context, index) {
                        if (index == 0) {
                          // QR scan card at top
                          return Card(
                            color: Colors.deepPurple.withAlpha(38),
                            child: ListTile(
                              leading: const Icon(Icons.qr_code_scanner,
                                  size: 48, color: Colors.deepPurple),
                              title: const Text('Scan QR Code'),
                              subtitle: const Text('Scan the QR code shown on your PC'),
                              trailing: const Icon(Icons.arrow_forward_ios),
                              onTap: _openQRScanner,
                            ),
                          );
                        }
                        final server = _servers[index - 1];
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

// ─── QR Scanner Screen ──────────────────────────────────────────────────

class _QRScannerScreen extends StatefulWidget {
  final void Function(String data) onScanned;

  const _QRScannerScreen({required this.onScanned});

  @override
  State<_QRScannerScreen> createState() => _QRScannerScreenState();
}

class _QRScannerScreenState extends State<_QRScannerScreen> {
  final MobileScannerController _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.normal,
    facing: CameraFacing.back,
  );
  bool _scanned = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Scan QR Code'),
        backgroundColor: Colors.black,
        actions: [
          IconButton(
            icon: ValueListenableBuilder(
              valueListenable: _controller,
              builder: (context, state, child) {
                if (state.torchState == TorchState.on) {
                  return const Icon(Icons.flash_on, color: Colors.amber);
                }
                return const Icon(Icons.flash_off);
              },
            ),
            onPressed: () => _controller.toggleTorch(),
          ),
          IconButton(
            icon: const Icon(Icons.cameraswitch),
            onPressed: () => _controller.switchCamera(),
          ),
        ],
      ),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: (capture) {
              if (_scanned) return;
              final barcode = capture.barcodes.firstOrNull;
              if (barcode?.rawValue != null) {
                setState(() => _scanned = true);
                widget.onScanned(barcode!.rawValue!);
              }
            },
          ),
          // Scan overlay
          Center(
            child: Container(
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.deepPurple, width: 3),
                borderRadius: BorderRadius.circular(16),
              ),
            ),
          ),
          // Instruction text
          Positioned(
            bottom: 60,
            left: 0,
            right: 0,
            child: const Text(
              'Point your camera at the QR code\nshown on the NexRemote PC app',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}