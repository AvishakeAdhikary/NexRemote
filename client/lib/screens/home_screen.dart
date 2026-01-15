import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
  final _manualIPController = TextEditingController();

  @override
  void dispose() {
    _pairingController.dispose();
    _manualIPController.dispose();
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
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: _showDebugInfo,
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Info card
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Card(
                color: Colors.blue.withOpacity(0.1),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      const Icon(Icons.info_outline, size: 48, color: Colors.blue),
                      const SizedBox(height: 16),
                      const Text(
                        'Connection Methods',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'WiFi: Automatic discovery\n'
                        'USB: Requires ADB setup\n'
                        'Manual: Enter IP address',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            
            // WiFi scan button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: ElevatedButton.icon(
                onPressed: _scanning ? null : _scanForPCs,
                icon: _scanning
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.wifi),
                label: Text(_scanning ? 'Scanning WiFi...' : 'Scan for PCs (WiFi)'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                  backgroundColor: Colors.blue,
                ),
              ),
            ),
            
            const SizedBox(height: 12),
            
            // USB connection button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: ElevatedButton.icon(
                onPressed: () => _connectViaUSB(network),
                icon: const Icon(Icons.usb),
                label: const Text('Connect via USB (ADB)'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                  backgroundColor: Colors.green,
                ),
              ),
            ),
            
            const SizedBox(height: 12),
            
            // Manual connection button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: ElevatedButton.icon(
                onPressed: () => _connectManually(network),
                icon: const Icon(Icons.edit),
                label: const Text('Manual IP Connection'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                  backgroundColor: Colors.orange,
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Device list or status
            if (_scanning)
              const Padding(
                padding: EdgeInsets.all(32.0),
                child: Column(
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Searching for PCs on local network...'),
                  ],
                ),
              )
            else if (_devices.isEmpty)
              Padding(
                padding: const EdgeInsets.all(32.0),
                child: Column(
                  children: [
                    Icon(Icons.computer_outlined, size: 64, color: Colors.grey[600]),
                    const SizedBox(height: 16),
                    Text(
                      'No PCs found via WiFi\n\n'
                      'Troubleshooting:\n'
                      '• Both devices on same WiFi?\n'
                      '• Windows server started?\n'
                      '• Windows running as Admin?\n'
                      '• Firewall allowing connection?\n\n'
                      'Try USB or Manual connection',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey[400]),
                    ),
                  ],
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
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
              
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildControlPanel(NetworkService network) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          children: [
            Text(network.pcName),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  network.isUSB ? Icons.usb : Icons.wifi,
                  size: 14,
                  color: Colors.greenAccent,
                ),
                const SizedBox(width: 4),
                const Text(
                  'Connected',
                  style: TextStyle(fontSize: 12, color: Colors.greenAccent),
                ),
              ],
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
          _buildControlCard('Gamepad', Icons.gamepad, Colors.blue,
              () => Navigator.push(context, MaterialPageRoute(builder: (_) => const GamepadScreen()))),
          _buildControlCard('Mouse', Icons.mouse, Colors.green,
              () => Navigator.push(context, MaterialPageRoute(builder: (_) => const MouseScreen()))),
          _buildControlCard('Keyboard', Icons.keyboard, Colors.orange,
              () => Navigator.push(context, MaterialPageRoute(builder: (_) => const KeyboardScreen()))),
          _buildControlCard('Media', Icons.music_note, Colors.purple,
              () => Navigator.push(context, MaterialPageRoute(builder: (_) => const MediaScreen()))),
          _buildControlCard('Files', Icons.folder, Colors.red,
              () => Navigator.push(context, MaterialPageRoute(builder: (_) => const FileBrowserScreen()))),
          _buildControlCard('About', Icons.info, Colors.grey, () => _showAbout()),
        ],
      ),
    );
  }

  Widget _buildControlCard(String title, IconData icon, Color color, VoidCallback onTap) {
    return Card(
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 60, color: color),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
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
        SnackBar(
          content: const Text(
            'No PCs found via WiFi.\n'
            'Try:\n'
            '1. Check both devices on same WiFi\n'
            '2. Windows server is started\n'
            '3. Use USB or Manual connection'
          ),
          duration: const Duration(seconds: 5),
          action: SnackBarAction(
            label: 'Debug',
            onPressed: _showDebugInfo,
          ),
        ),
      );
    }
  }

  Future<void> _connectViaUSB(NetworkService network) async {
    // Show ADB setup instructions
    final proceed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('USB Connection (ADB)'),
        content: const SingleChildScrollView(
          child: Text(
            'Prerequisites:\n\n'
            '1. Enable USB Debugging on Android:\n'
            '   Settings → Developer Options → USB Debugging\n\n'
            '2. Install ADB on PC (if not installed)\n\n'
            '3. Connect phone via USB cable\n\n'
            '4. Run these commands on PC:\n'
            '   adb forward tcp:8888 tcp:8888\n'
            '   adb forward tcp:8889 tcp:8889\n\n'
            '5. Keep USB connected during use\n\n'
            'Have you completed these steps?',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Not Yet'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Yes, Connect'),
          ),
        ],
      ),
    );
    
    if (proceed != true) return;
    
    // Create USB device
    final device = PCDevice.usb('PC via USB');
    await _connectToDevice(device, network);
  }

  Future<void> _connectManually(NetworkService network) async {
    _manualIPController.text = '192.168.0.240'; // Pre-fill with known IP
    
    final ip = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Manual IP Connection'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Enter your PC\'s IP address:'),
            const SizedBox(height: 16),
            TextField(
              controller: _manualIPController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                hintText: '192.168.0.240',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.computer),
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
            onPressed: () => Navigator.pop(context, _manualIPController.text),
            child: const Text('Connect'),
          ),
        ],
      ),
    );
    
    if (ip == null || ip.isEmpty) return;
    
    // Create device from manual IP
    final device = PCDevice(
      name: 'PC at $ip',
      ipAddress: ip,
      port: 8888,
      version: '2.0',
      requiresPairing: true,
    );
    
    await _connectToDevice(device, network);
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
              Expanded(child: Text('Connecting...\nCheck debug console for details')),
            ],
          ),
        ),
      ),
    );
    
    final success = await network.connectToPC(device, pairingCode);
    Navigator.pop(context);
    
    if (!success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text(
            'Connection failed!\n'
            'Check:\n'
            '• Pairing code correct\n'
            '• Windows server running\n'
            '• Firewall not blocking'
          ),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 5),
          action: SnackBarAction(
            label: 'Debug',
            textColor: Colors.white,
            onPressed: _showDebugInfo,
          ),
        ),
      );
    }
  }
  
  void _showDebugInfo() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Debug Information'),
        content: SingleChildScrollView(
          child: Text(
            'Debug Console Output:\n\n'
            'Check your IDE console or run:\n'
            'flutter logs\n\n'
            'Look for:\n'
            '• "=== DISCOVERY START ==="\n'
            '• "Local WiFi IP: ..."\n'
            '• "Sent X bytes to ..."\n'
            '• "Received from ..."\n'
            '• Any error messages\n\n'
            'Common Issues:\n\n'
            '1. Different WiFi networks\n'
            '   → Ensure both on same WiFi\n\n'
            '2. Firewall blocking\n'
            '   → Run Windows as Admin\n'
            '   → Check Windows Firewall\n\n'
            '3. Router AP Isolation\n'
            '   → Disable in router settings\n\n'
            '4. Wrong subnet\n'
            '   → Your IP: 192.168.0.32\n'
            '   → PC should be: 192.168.0.X\n\n'
            'Try Manual Connection with:\n'
            'IP: 192.168.0.240\n'
            'Port: 8888',
            style: TextStyle(fontSize: 12, fontFamily: 'monospace'),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              Clipboard.setData(const ClipboardData(text: '192.168.0.240'));
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('IP copied to clipboard')),
              );
            },
            child: const Text('Copy PC IP'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
  
  void _showAbout() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('NexRemote'),
        content: const SingleChildScrollView(
          child: Text(
            'Features:\n'
            '✓ Encrypted connection\n'
            '✓ Pairing code authentication\n'
            '✓ WiFi connection\n'
            '✓ USB connection (ADB)\n'
            '✓ Manual IP connection\n'
            '✓ Multi-client support\n'
            '✓ Full gamepad emulation\n'
            '✓ Mouse & keyboard control\n'
            '✓ Media controls\n'
            '✓ File browsing\n\n'
            'Connection Methods:\n\n'
            'WiFi: Automatic discovery\n'
            '• Both devices same network\n'
            '• Windows server running\n\n'
            'USB: Via ADB forwarding\n'
            '• USB debugging enabled\n'
            '• ADB commands run on PC\n\n'
            'Manual: Direct IP entry\n'
            '• For troubleshooting\n'
            '• When discovery fails',
          ),
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