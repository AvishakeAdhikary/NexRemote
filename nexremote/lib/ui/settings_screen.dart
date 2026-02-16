import 'package:flutter/material.dart';
import '../utils/config.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final Config _config = Config();
  final TextEditingController _deviceNameController = TextEditingController();
  
  bool _autoConnect = false;
  double _gyroSensitivity = 1.0;
  
  @override
  void initState() {
    super.initState();
    _loadSettings();
  }
  
  Future<void> _loadSettings() async {
    await _config.init();
    setState(() {
      _deviceNameController.text = _config.deviceName;
      _autoConnect = _config.autoConnect;
      _gyroSensitivity = _config.gyroSensitivity;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          ListTile(
            title: const Text('Device Name'),
            subtitle: TextField(
              controller: _deviceNameController,
              decoration: const InputDecoration(
                hintText: 'Enter device name',
              ),
              onChanged: (value) {
                _config.setDeviceName(value);
              },
            ),
          ),
          SwitchListTile(
            title: const Text('Auto Connect'),
            subtitle: const Text('Automatically connect to last server'),
            value: _autoConnect,
            onChanged: (value) {
              setState(() {
                _autoConnect = value;
              });
              _config.setAutoConnect(value);
            },
          ),
          ListTile(
            title: const Text('Gyroscope Sensitivity'),
            subtitle: Text('Current: ${_gyroSensitivity.toStringAsFixed(1)}'),
            trailing: SizedBox(
              width: 200,
              child: Slider(
                value: _gyroSensitivity,
                min: 0.1,
                max: 5.0,
                divisions: 49,
                onChanged: (value) async {
                  setState(() {
                    _gyroSensitivity = value;
                  });
                  await _config.setGyroSensitivity(value);
                },
              ),
            ),
          ),
          ListTile(
            title: const Text('About'),
            subtitle: const Text('NexRemote v1.0.0'),
            leading: const Icon(Icons.info),
          ),
        ],
      ),
    );
  }
  
  @override
  void dispose() {
    _deviceNameController.dispose();
    super.dispose();
  }
}