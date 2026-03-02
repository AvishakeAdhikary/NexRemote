import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
            Icon(Icons.cast_connected, color: Colors.blue, size: 28),
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
      floatingActionButton:
          _connectionState == conn.ConnectionState.disconnected
          ? Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                FloatingActionButton.extended(
                  heroTag: 'usb_connect',
                  onPressed: () => _connectViaUsb(),
                  icon: const Icon(Icons.usb),
                  label: const Text('USB'),
                  backgroundColor: Colors.green,
                ),
                const SizedBox(height: 12),
                FloatingActionButton.extended(
                  heroTag: 'wifi_connect',
                  onPressed: () => _navigateToConnection(),
                  icon: const Icon(Icons.wifi),
                  label: const Text('Wi-Fi'),
                ),
              ],
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
        border: Border(bottom: BorderSide(color: statusColor, width: 2)),
      ),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              statusText,
              style: TextStyle(color: statusColor, fontWeight: FontWeight.bold),
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
            Icon(feature.icon, size: 48, color: feature.color),
            const SizedBox(height: 12),
            Text(
              feature.title,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
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
          Icon(
            Icons.cast_connected,
            size: 120,
            color: Colors.blue.withValues(alpha: 0.7),
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
            'Connect via Wi-Fi or USB tethering',
            style: TextStyle(fontSize: 16, color: Colors.grey[500]),
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
        builder: (context) =>
            ConnectionScreen(connectionManager: _connectionManager),
      ),
    );

    if (result == true) {
      Logger.info('Connected successfully');
    }
  }

  void _connectViaUsb() async {
    final scaffoldMsg = ScaffoldMessenger.of(context);
    scaffoldMsg.showSnackBar(
      const SnackBar(
        content: Text('Connecting via USB (ADB)...'),
        duration: Duration(seconds: 2),
      ),
    );

    final success = await _connectionManager.connectUsb(
      'nexremote-device',
      'NexRemote Mobile',
    );

    if (!mounted) return;

    if (success) {
      scaffoldMsg.showSnackBar(
        const SnackBar(
          content: Text('Connected via USB!'),
          backgroundColor: Colors.green,
        ),
      );
    } else {
      // Show guidance dialog
      _showUsbSetupGuide();
    }
  }

  void _showUsbSetupGuide() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF2A2A2A),
        title: const Row(
          children: [
            Icon(Icons.usb, color: Colors.orange, size: 28),
            SizedBox(width: 12),
            Text('USB Setup Required', style: TextStyle(color: Colors.white)),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'USB connection requires USB Debugging to be enabled '
                'on your phone and ADB installed on the PC.',
                style: TextStyle(color: Colors.white70, fontSize: 14),
              ),
              const SizedBox(height: 16),
              _guideStep(
                '1',
                'Enable Developer Options',
                'Go to Settings → About Phone → tap "Build Number" 7 times',
              ),
              _guideStep(
                '2',
                'Enable USB Debugging',
                'Settings → Developer Options → toggle "USB Debugging"',
              ),
              _guideStep(
                '3',
                'Connect USB cable',
                'Connect your phone to the PC with a USB cable',
              ),
              _guideStep(
                '4',
                'Accept USB debugging prompt',
                'Tap "Allow" on the RSA fingerprint dialog on your phone',
              ),
              _guideStep(
                '5',
                'Ensure NexRemote server is running',
                'The server auto-detects ADB and sets up port forwarding',
              ),
              const Divider(color: Colors.white24),
              const SizedBox(height: 8),
              const Text(
                'Quick Actions:',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _openAndroidSettings(
                        'android.settings.APPLICATION_DEVELOPMENT_SETTINGS',
                      ),
                      icon: const Icon(
                        Icons.developer_mode,
                        color: Colors.green,
                      ),
                      label: const Text(
                        'Developer\nOptions',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white, fontSize: 12),
                      ),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Colors.green),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _openAndroidSettings(
                        'android.settings.DEVICE_INFO_SETTINGS',
                      ),
                      icon: const Icon(Icons.info_outline, color: Colors.blue),
                      label: const Text(
                        'Build\nNumber',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white, fontSize: 12),
                      ),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Colors.blue),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              _connectViaUsb();
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
            child: const Text('Retry', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Widget _guideStep(String number, String title, String subtitle) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.blue.withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: Text(
              number,
              style: const TextStyle(
                color: Colors.blue,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _openAndroidSettings(String action) {
    // Use platform channel to open Android settings
    const platform = MethodChannel('com.nexremote/settings');
    platform.invokeMethod('openSettings', {'action': action}).catchError((_) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Could not open settings automatically. '
            'Please navigate there manually.',
          ),
          backgroundColor: Colors.orange,
        ),
      );
    });
  }

  void _navigateToGamepad() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            GamepadScreen(connectionManager: _connectionManager),
      ),
    );
  }

  void _navigateToTouchpad() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            TouchpadScreen(connectionManager: _connectionManager),
      ),
    );
  }

  void _navigateToFileExplorer() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            FileExplorerScreen(connectionManager: _connectionManager),
      ),
    );
  }

  void _navigateToCamera() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            CameraScreen(connectionManager: _connectionManager),
      ),
    );
  }

  void _navigateToScreenShare() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            ScreenShareScreen(connectionManager: _connectionManager),
      ),
    );
  }

  void _navigateToMediaControl() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            MediaControlScreen(connectionManager: _connectionManager),
      ),
    );
  }

  void _navigateToTaskManager() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            TaskManagerScreen(connectionManager: _connectionManager),
      ),
    );
  }

  void _showSettings() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const SettingsScreen()),
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
