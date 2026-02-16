import 'package:flutter/material.dart';
import '../core/connection_manager.dart' as conn;
import '../utils/logger.dart';
import 'connection_screen.dart';
import 'gamepad_screen.dart';
import 'touchpad_screen.dart';
import 'camera_screen.dart';
import 'file_explorer_screen.dart';
import 'screen_share_screen.dart';
import 'media_control_screen.dart';
import 'task_manager_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final conn.ConnectionManager _connectionManager = conn.ConnectionManager();
  conn.ConnectionState _connectionState = conn.ConnectionState.disconnected;
  String _connectedDeviceName = '';

  @override
  void initState() {
    super.initState();
    _connectionManager.connectionStateStream.listen((state) {
      setState(() {
        _connectionState = state;
      });
    });
    
    _connectionManager.connectedDeviceStream.listen((deviceName) {
      setState(() {
        _connectedDeviceName = deviceName;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset(
              '../shared/assets/logo.png',
              width: 32,
              height: 32,
            ),
            const SizedBox(width: 10),
            const Text('NexRemote'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showSettings(),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildConnectionStatus(),
          Expanded(
            child: _connectionState == conn.ConnectionState.connected
                ? _buildFeatureGrid()
                : _buildConnectPrompt(),
          ),
        ],
      ),
      floatingActionButton: _connectionState == conn.ConnectionState.disconnected
          ? FloatingActionButton.extended(
              onPressed: () => _navigateToConnection(),
              icon: const Icon(Icons.wifi),
              label: const Text('Connect to PC'),
            )
          : null,
    );
  }

  Widget _buildConnectionStatus() {
    Color statusColor;
    String statusText;
    IconData statusIcon;

    switch (_connectionState) {
      case conn.ConnectionState.connected:
        statusColor = Colors.green;
        statusText = 'Connected to $_connectedDeviceName';
        statusIcon = Icons.check_circle;
        break;
      case conn.ConnectionState.connecting:
        statusColor = Colors.orange;
        statusText = 'Connecting...';
        statusIcon = Icons.sync;
        break;
      default:
        statusColor = Colors.red;
        statusText = 'Disconnected';
        statusIcon = Icons.cancel;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.2),
        border: Border(
          bottom: BorderSide(color: statusColor, width: 2),
        ),
      ),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              statusText,
              style: TextStyle(
                color: statusColor,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          if (_connectionState == conn.ConnectionState.connected)
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () => _disconnect(),
              color: Colors.white70,
            ),
        ],
      ),
    );
  }

  Widget _buildFeatureGrid() {
    final features = [
      _FeatureItem(
        'Gamepad',
        Icons.videogame_asset,
        Colors.blue,
        () => _navigateToGamepad(),
      ),
      _FeatureItem(
        'Touchpad',
        Icons.touch_app,
        Colors.purple,
        () => _navigateToTouchpad(),
      ),
      _FeatureItem(
        'File Explorer',
        Icons.folder,
        Colors.orange,
        () => _navigateToFileExplorer(),
      ),
      _FeatureItem(
        'Camera',
        Icons.camera_alt,
        Colors.red,
        () => _navigateToCamera(),
      ),
      _FeatureItem(
        'Screen Share',
        Icons.screen_share,
        Colors.teal,
        () => _navigateToScreenShare(),
      ),
      _FeatureItem(
        'Media Control',
        Icons.music_note,
        Colors.pink,
        () => _navigateToMediaControl(),
      ),
      _FeatureItem(
        'Task Manager',
        Icons.task,
        Colors.indigo,
        () => _navigateToTaskManager(),
      ),
    ];

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 1.2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: features.length,
      itemBuilder: (context, index) {
        final feature = features[index];
        return _buildFeatureCard(feature);
      },
    );
  }

  Widget _buildFeatureCard(_FeatureItem feature) {
    return Card(
      child: InkWell(
        onTap: feature.onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              feature.icon,
              size: 48,
              color: feature.color,
            ),
            const SizedBox(height: 12),
            Text(
              feature.title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectPrompt() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Image.asset(
            '../shared/assets/logo.png',
            width: 120,
            height: 120,
          ),
          const SizedBox(height: 24),
          Text(
            'Not Connected',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Colors.grey[400],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Tap the button below to connect to your PC',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[500],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  void _navigateToConnection() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ConnectionScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );

    if (result == true) {
      Logger.info('Connected successfully');
    }
  }

  void _navigateToGamepad() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => GamepadScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );
  }

  void _navigateToTouchpad() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => TouchpadScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );
  }

  void _navigateToFileExplorer() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => FileExplorerScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );
  }

  void _navigateToCamera() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CameraScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );
  }

  void _navigateToScreenShare() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ScreenShareScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );
  }

  void _navigateToMediaControl() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => MediaControlScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );
  }

  void _navigateToTaskManager() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => TaskManagerScreen(
          connectionManager: _connectionManager,
        ),
      ),
    );
  }

  void _showFeature(String featureName) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$featureName feature coming soon!'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _showSettings() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const SettingsScreen(),
      ),
    );
  }

  void _disconnect() {
    _connectionManager.disconnect();
  }

  @override
  void dispose() {
    _connectionManager.dispose();
    super.dispose();
  }
}

class _FeatureItem {
  final String title;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  _FeatureItem(this.title, this.icon, this.color, this.onTap);
}