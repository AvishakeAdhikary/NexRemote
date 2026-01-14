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
              ),
            ),
          ),
          Expanded(
            child: _devices.isEmpty
                ? const Center(
                    child: Text(
                      'No PCs found.\nMake sure the Windows app is running.',
                      textAlign: TextAlign.center,
                    ),
                  )
                : ListView.builder(
                    itemCount: _devices.length,
                    itemBuilder: (context, index) {
                      final device = _devices[index];
                      return Card(
                        margin: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 8,
                        ),
                        child: ListTile(
                          leading: const Icon(Icons.computer, size: 40),
                          title: Text(device.name),
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
        title: Text(network.pcName),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: network.disconnect,
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
            'Settings',
            Icons.settings,
            Colors.grey,
            () {},
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
    setState(() => _scanning = true);
    final network = Provider.of<NetworkService>(context, listen: false);
    final devices = await network.discoverPCs();
    setState(() {
      _devices = devices;
      _scanning = false;
    });
  }

  Future<void> _connectToDevice(PCDevice device, NetworkService network) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );
    final success = await network.connectToPC(device);
    Navigator.pop(context);
    if (!success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to connect')),
      );
    }
  }
}
