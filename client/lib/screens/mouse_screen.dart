import 'package:flutter/material.dart';
import 'package:nexremote/services/network_service.dart';
import 'package:provider/provider.dart';

class MouseScreen extends StatefulWidget {
  const MouseScreen({Key? key}) : super(key: key);
  @override
  State<MouseScreen> createState() => _MouseScreenState();
}

class _MouseScreenState extends State<MouseScreen> {
  void _sendMouseMove(double dx, double dy) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network.sendCommand('mouse_move', {'dx': dx, 'dy': dy});
  }

  void _sendMouseClick(String button, {bool double_click = false}) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network
        .sendCommand('mouse_click', {'button': button, 'double': double_click});
  }

  void _sendScroll(double dx, double dy) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network.sendCommand('mouse_scroll', {'dx': dx, 'dy': dy});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mouse Controller')),
      body: Column(
        children: [
          Expanded(
            flex: 3,
            child: GestureDetector(
              onPanUpdate: (details) {
                _sendMouseMove(details.delta.dx * 2, details.delta.dy * 2);
              },
              child: Container(
                color: Colors.grey[900],
                child: const Center(
                  child: Text(
                    'TOUCHPAD',
                    style: TextStyle(fontSize: 24, color: Colors.grey),
                  ),
                ),
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildMouseButton('LEFT', () => _sendMouseClick('left')),
                _buildMouseButton('MIDDLE', () => _sendMouseClick('middle')),
                _buildMouseButton('RIGHT', () => _sendMouseClick('right')),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  icon: const Icon(Icons.arrow_upward, size: 32),
                  onPressed: () => _sendScroll(0, 5),
                ),
                const SizedBox(width: 20),
                const Text('SCROLL', style: TextStyle(fontSize: 16)),
                const SizedBox(width: 20),
                IconButton(
                  icon: const Icon(Icons.arrow_downward, size: 32),
                  onPressed: () => _sendScroll(0, -5),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMouseButton(String label, VoidCallback onTap) {
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        minimumSize: const Size(100, 60),
        backgroundColor: Colors.blue,
      ),
      child: Text(label, style: const TextStyle(fontSize: 16)),
    );
  }
}
