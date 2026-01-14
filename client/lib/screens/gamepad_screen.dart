import 'package:flutter/material.dart';
import 'package:nexremote/services/network_service.dart';
import 'package:nexremote/widgets/game_button.dart';
import 'package:provider/provider.dart';

class GamepadScreen extends StatefulWidget {
  const GamepadScreen({Key? key}) : super(key: key);
  @override
  State<GamepadScreen> createState() => _GamepadScreenState();
}

class _GamepadScreenState extends State<GamepadScreen> {
  Offset _leftStick = Offset.zero;
  Offset _rightStick = Offset.zero;
  void _sendButton(String button, bool pressed) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network
        .sendCommand('gamepad_button', {'button': button, 'pressed': pressed});
  }

  void _sendAxis(String axis, double value) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network.sendCommand('gamepad_axis', {'axis': axis, 'value': value});
  }

  void _sendTrigger(String trigger, double value) {
    final network = Provider.of<NetworkService>(context, listen: false);
    network
        .sendCommand('gamepad_trigger', {'trigger': trigger, 'value': value});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('Gamepad Controller'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: SafeArea(
        child: Stack(
          children: [
// Left side - D-pad and Left Stick
            Positioned(
              left: 20,
              top: 50,
              child: Column(
                children: [
                  _buildDPad(),
                  const SizedBox(height: 40),
                  _buildAnalogStick(
                    onChanged: (offset) {
                      setState(() => _leftStick = offset);
                      _sendAxis('left_x', offset.dx);
                      _sendAxis('left_y', -offset.dy);
                    },
                  ),
                  const SizedBox(height: 10),
                  GameButton(
                    label: 'L3',
                    onPressed: () => _sendButton('l3', true),
                    onReleased: () => _sendButton('l3', false),
                    color: Colors.grey,
                    size: 50,
                  ),
                ],
              ),
            ),
// Right side - Action buttons and Right Stick
            Positioned(
              right: 20,
              top: 50,
              child: Column(
                children: [
                  _buildActionButtons(),
                  const SizedBox(height: 40),
                  _buildAnalogStick(
                    onChanged: (offset) {
                      setState(() => _rightStick = offset);
                      _sendAxis('right_x', offset.dx);
                      _sendAxis('right_y', -offset.dy);
                    },
                  ),
                  const SizedBox(height: 10),
                  GameButton(
                    label: 'R3',
                    onPressed: () => _sendButton('r3', true),
                    onReleased: () => _sendButton('r3', false),
                    color: Colors.grey,
                    size: 50,
                  ),
                ],
              ),
            ),
// Top - Triggers and Bumpers
            Positioned(
              top: 20,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    children: [
                      _buildTrigger('L2', () => _sendTrigger('lt', 1.0),
                          () => _sendTrigger('lt', 0.0)),
                      GameButton(
                        label: 'L1',
                        onPressed: () => _sendButton('lb', true),
                        onReleased: () => _sendButton('lb', false),
                        size: 60,
                      ),
                    ],
                  ),
                  Column(
                    children: [
                      _buildTrigger('R2', () => _sendTrigger('rt', 1.0),
                          () => _sendTrigger('rt', 0.0)),
                      GameButton(
                        label: 'R1',
                        onPressed: () => _sendButton('rb', true),
                        onReleased: () => _sendButton('rb', false),
                        size: 60,
                      ),
                    ],
                  ),
                ],
              ),
            ),
// Center - Start and Select
            Positioned(
              bottom: 120,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  GameButton(
                    label: 'SELECT',
                    onPressed: () => _sendButton('back', true),
                    onReleased: () => _sendButton('back', false),
                    color: Colors.grey,
                    size: 50,
                  ),
                  const SizedBox(width: 40),
                  GameButton(
                    label: 'START',
                    onPressed: () => _sendButton('start', true),
                    onReleased: () => _sendButton('start', false),
                    color: Colors.grey,
                    size: 50,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDPad() {
    return SizedBox(
      width: 150,
      height: 150,
      child: Stack(
        children: [
          Positioned(
            top: 0,
            left: 50,
            child: GameButton(
              label: '▲',
              onPressed: () => _sendButton('up', true),
              onReleased: () => _sendButton('up', false),
              size: 50,
            ),
          ),
          Positioned(
            bottom: 0,
            left: 50,
            child: GameButton(
              label: '▼',
              onPressed: () => _sendButton('down', true),
              onReleased: () => _sendButton('down', false),
              size: 50,
            ),
          ),
          Positioned(
            left: 0,
            top: 50,
            child: GameButton(
              label: '◄',
              onPressed: () => _sendButton('left', true),
              onReleased: () => _sendButton('left', false),
              size: 50,
            ),
          ),
          Positioned(
            right: 0,
            top: 50,
            child: GameButton(
              label: '►',
              onPressed: () => _sendButton('right', true),
              onReleased: () => _sendButton('right', false),
              size: 50,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return SizedBox(
      width: 150,
      height: 150,
      child: Stack(
        children: [
          Positioned(
            top: 0,
            left: 50,
            child: GameButton(
              label: 'Y',
              onPressed: () => _sendButton('y', true),
              onReleased: () => _sendButton('y', false),
              color: Colors.yellow,
              size: 50,
            ),
          ),
          Positioned(
            bottom: 0,
            left: 50,
            child: GameButton(
              label: 'A',
              onPressed: () => _sendButton('a', true),
              onReleased: () => _sendButton('a', false),
              color: Colors.green,
              size: 50,
            ),
          ),
          Positioned(
            left: 0,
            top: 50,
            child: GameButton(
              label: 'X',
              onPressed: () => _sendButton('x', true),
              onReleased: () => _sendButton('x', false),
              color: Colors.blue,
              size: 50,
            ),
          ),
          Positioned(
            right: 0,
            top: 50,
            child: GameButton(
              label: 'B',
              onPressed: () => _sendButton('b', true),
              onReleased: () => _sendButton('b', false),
              color: Colors.red,
              size: 50,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalogStick({required Function(Offset) onChanged}) {
    return GestureDetector(
      onPanUpdate: (details) {
        final RenderBox box = context.findRenderObject() as RenderBox;
        final center = Offset(75, 75);
        final localPosition = details.localPosition - center;
        final distance = localPosition.distance;
        if (distance > 50) {
          final normalized = localPosition / distance;
          onChanged(normalized);
        } else {
          onChanged(localPosition / 50);
        }
      },
      onPanEnd: (_) => onChanged(Offset.zero),
      child: Container(
        width: 150,
        height: 150,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.grey[800],
          border: Border.all(color: Colors.blue, width: 3),
        ),
        child: Center(
          child: Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.blue,
              boxShadow: [
                BoxShadow(
                  color: Colors.blue.withOpacity(0.5),
                  blurRadius: 15,
                  spreadRadius: 5,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTrigger(
      String label, VoidCallback onPressed, VoidCallback onReleased) {
    return GestureDetector(
      onTapDown: (_) => onPressed(),
      onTapUp: (_) => onReleased(),
      onTapCancel: onReleased,
      child: Container(
        width: 80,
        height: 40,
        margin: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          color: Colors.grey[700],
          border: Border.all(color: Colors.blue),
        ),
        child: Center(
          child: Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      ),
    );
  }
}
