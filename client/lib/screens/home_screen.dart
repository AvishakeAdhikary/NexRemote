import 'package:flutter/material.dart';
import 'package:nexremote/models/pc_device.dart';
import 'package:nexremote/screens/file_browser_screen.dart';
import 'package:nexremote/screens/gamepad_screen.dart';
import 'package:nexremote/screens/keyboard_screen.dart';
import 'package:nexremote/screens/media_screen.dart';
import 'package:nexremote/screens/mouse_screen.dart';
import 'package:nexremote/services/network_service.dart';
import 'package:provider/provider.dart';


class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<PCDevice> _devices = [];
  bool _scanning = false;
  final _pairingController = TextEditingController();

  @override
  void dispose() {
    _pairingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<NetworkService>(
      builder: (context, network, _) {
        if (network.connected) {
          return _buildControlPanel(network);
        } else {
          return _buildConnectionScreen(network);
        }
      },
    );
  }

  Widget _buildConnectionScreen(NetworkService network) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('NexRemote'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Icon(Icons.info_outline, size: 48, color: Colors.blue),
                    const SizedBox(height: 16),
                    const Text(
                      'How to Connect',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '1. Start the server on your Windows PC\n'
                      '2. Tap "Scan for PCs" below\n'
                      '3. Select your PC from the list\n'
                      '4. Enter the 6-digit pairing code\n'
                      '   shown on your PC screen',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 14),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: ElevatedButton.icon(
              onPressed: _scanning ? null : _scanForPCs,
              icon: _scanning
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.search),
              label: Text(_scanning ? 'Scanning...' : 'Scan for PCs'),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 50),
                backgroundColor: Colors.blue,
              ),
            ),
          ),
          Expanded(
            child: _devices.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.computer, size: 64, color: Colors.grey[600]),
                        const SizedBox(height: 16),
                        Text(
                          _scanning 
                            ? 'Searching for PCs...'
                            : 'No PCs found\n\nMake sure:\n'
                              '• Windows app is running\n'
                              '• Server is started\n'
                              '• Both devices on same Wi-Fi',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey[400]),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    itemCount: _devices.length,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemBuilder: (context, index) {
                      final device = _devices[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: ListTile(
                          leading: const Icon(Icons.computer, size: 40, color: Colors.blue),
                          title: Text(
                            device.name,
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          subtitle: Text('${device.ipAddress}:${device.port}'),
                          trailing: const Icon(Icons.arrow_forward),
                          onTap: () => _connectToDevice(device, network),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildControlPanel(NetworkService network) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          children: [
            Text(network.pcName),
            Text(
              'Connected',
              style: const TextStyle(fontSize: 12, color: Colors.greenAccent),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => AlertDialog(
                  title: const Text('Disconnect'),
                  content: const Text('Do you want to disconnect from the PC?'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Cancel'),
                    ),
                    TextButton(
                      onPressed: () {
                        network.disconnect();
                        Navigator.pop(context);
                      },
                      child: const Text('Disconnect'),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
      body: GridView.count(
        crossAxisCount: 2,
        padding: const EdgeInsets.all(16),
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        children: [
          _buildControlCard(
            'Gamepad',
            Icons.gamepad,
            Colors.blue,
            () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const GamepadScreen()),
            ),
          ),
          _buildControlCard(
            'Mouse',
            Icons.mouse,
            Colors.green,
            () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const MouseScreen()),
            ),
          ),
          _buildControlCard(
            'Keyboard',
            Icons.keyboard,
            Colors.orange,
            () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const KeyboardScreen()),
            ),
          ),
          _buildControlCard(
            'Media',
            Icons.music_note,
            Colors.purple,
            () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const MediaScreen()),
            ),
          ),
          _buildControlCard(
            'Files',
            Icons.folder,
            Colors.red,
            () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const FileBrowserScreen()),
            ),
          ),
          _buildControlCard(
            'About',
            Icons.info,
            Colors.grey,
            () => _showAbout(),
          ),
        ],
      ),
    );
  }

  Widget _buildControlCard(
    String title,
    IconData icon,
    Color color,
    VoidCallback onTap,
  ) {
    return Card(
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 60, color: color),
            const SizedBox(height: 8),
            Text(
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _scanForPCs() async {
    setState(() {
      _scanning = true;
      _devices.clear();
    });
    
    final network = Provider.of<NetworkService>(context, listen: false);
    final devices = await network.discoverPCs();
    
    setState(() {
      _devices = devices;
      _scanning = false;
    });
    
    if (devices.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No PCs found. Make sure Windows server is running.'),
          duration: Duration(seconds: 3),
        ),
      );
    }
  }

  Future<void> _connectToDevice(PCDevice device, NetworkService network) async {
    // Show pairing code dialog
    _pairingController.clear();
    
    final pairingCode = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Enter Pairing Code'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Enter the 6-digit code shown\non ${device.name}',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _pairingController,
              keyboardType: TextInputType.number,
              maxLength: 6,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                letterSpacing: 8,
              ),
              decoration: const InputDecoration(
                hintText: '000000',
                border: OutlineInputBorder(),
                counterText: '',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (_pairingController.text.length == 6) {
                Navigator.pop(context, _pairingController.text);
              }
            },
            child: const Text('Connect'),
          ),
        ],
      ),
    );
    
    if (pairingCode == null) return;
    
    // Show connecting dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => WillPopScope(
        onWillPop: () async => false,
        child: const AlertDialog(
          content: Row(
            children: [
              CircularProgressIndicator(),
              SizedBox(width: 20),
              Text('Connecting...'),
            ],
          ),
        ),
      ),
    );
    
    final success = await network.connectToPC(device, pairingCode);
    Navigator.pop(context);
    
    if (!success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Connection failed. Check pairing code and try again.'),
          backgroundColor: Colors.red,
          duration: Duration(seconds: 3),
        ),
      );
    }
  }
  
  void _showAbout() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('NexRemote'),
        content: const Text(
          'Features:\n'
          '✓ Encrypted connection\n'
          '✓ Pairing code authentication\n'
          '✓ Multi-client support\n'
          '✓ Full gamepad emulation\n'
          '✓ Mouse & keyboard control\n'
          '✓ Media controls\n'
          '✓ File browsing\n\n'
          'Make sure both devices are on\n'
          'the same Wi-Fi network.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}