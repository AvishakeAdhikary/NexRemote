import 'package:flutter/material.dart';
import 'package:nexremote/services/network_service.dart';
import 'package:provider/provider.dart';

class KeyboardScreen extends StatefulWidget {
  const KeyboardScreen({Key? key}) : super(key: key);
  @override
  State<KeyboardScreen> createState() => _KeyboardScreenState();
}

class _KeyboardScreenState extends State<KeyboardScreen> {
  final _textController = TextEditingController();
  void _sendKey(String key) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network.sendCommand('key_press', {'key': key});
    Future.delayed(const Duration(milliseconds: 50), () {
      network.sendCommand('key_release', {'key': key});
    });
  }

  void _sendText(String text) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network.sendCommand('key_type', {'text': text});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Keyboard')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _textController,
              decoration: InputDecoration(
                hintText: 'Type here...',
                suffixIcon: IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: () {
                    _sendText(_textController.text);
                    _textController.clear();
                  },
                ),
              ),
            ),
          ),
          const Divider(),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _buildKeyRow(['Esc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6']),
                  const SizedBox(height: 8),
                  _buildKeyRow(
                      ['F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'Delete']),
                  const SizedBox(height: 16),
                  _buildKeyRow(
                      ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']),
                  const SizedBox(height: 8),
                  _buildKeyRow(
                      ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P']),
                  const SizedBox(height: 8),
                  _buildKeyRow(['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L']),
                  const SizedBox(height: 8),
                  _buildKeyRow(['Z', 'X', 'C', 'V', 'B', 'N', 'M']),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _buildSpecialKey('Ctrl', width: 80),
                      _buildSpecialKey('Alt', width: 80),
                      _buildSpecialKey('Space', width: 200),
                      _buildSpecialKey('Enter', width: 80),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _buildSpecialKey('↑'),
                    ],
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _buildSpecialKey('←'),
                      _buildSpecialKey('↓'),
                      _buildSpecialKey('→'),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildKeyRow(List<String> keys) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: keys.map((key) => _buildKey(key)).toList(),
    );
  }

  Widget _buildKey(String key) {
    return Padding(
      padding: const EdgeInsets.all(2),
      child: ElevatedButton(
        onPressed: () => _sendKey(key.toLowerCase()),
        style: ElevatedButton.styleFrom(
          minimumSize: const Size(35, 40),
          padding: const EdgeInsets.all(4),
        ),
        child: Text(key, style: const TextStyle(fontSize: 12)),
      ),
    );
  }

  Widget _buildSpecialKey(String key, {double width = 60}) {
    String keyCode = key.toLowerCase();
    if (key == '↑') keyCode = 'up';
    if (key == '↓') keyCode = 'down';
    if (key == '←') keyCode = 'left';
    if (key == '→') keyCode = 'right';
    return Padding(
      padding: const EdgeInsets.all(2),
      child: ElevatedButton(
        onPressed: () => _sendKey(keyCode),
        style: ElevatedButton.styleFrom(
          minimumSize: Size(width, 40),
        ),
        child: Text(key),
      ),
    );
  }
}
