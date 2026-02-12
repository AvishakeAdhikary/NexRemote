import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/gamepad_controller.dart';

class GamepadScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const GamepadScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<GamepadScreen> createState() => _GamepadScreenState();
}

class _GamepadScreenState extends State<GamepadScreen> {
  late GamepadController _gamepadController;
  StreamSubscription? _gyroSubscription;
  
  bool _gyroEnabled = false;
  Offset _leftStickOffset = Offset.zero;
  Offset _rightStickOffset = Offset.zero;

  @override
  void initState() {
    super.initState();
    _gamepadController = GamepadController(widget.connectionManager);
  }

  void _toggleGyro() {
    setState(() {
      _gyroEnabled = !_gyroEnabled;
    });

    if (_gyroEnabled) {
      _startGyro();
    } else {
      _stopGyro();
    }
  }

  void _startGyro() {
    _gyroSubscription = gyroscopeEvents.listen((GyroscopeEvent event) {
      _gamepadController.sendGyroData(event.x, event.y, event.z);
    });
  }

  void _stopGyro() {
    _gyroSubscription?.cancel();
  }

  @override
  Widget build(BuildContext context) {
    final isLandscape = MediaQuery.of(context).orientation == Orientation.landscape;
    
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('Gamepad'),
        actions: [
          IconButton(
            icon: Icon(
              _gyroEnabled ? Icons.motion_photos_on : Icons.motion_photos_off,
            ),
            onPressed: _toggleGyro,
          ),
        ],
      ),
      body: SafeArea(
        child: isLandscape
            ? _buildLandscapeLayout()
            : _buildPortraitLayout(),
      ),
    );
  }

  Widget _buildLandscapeLayout() {
    return Stack(
      children: [
        // Left side controls
        Positioned(
          left: 20,
          top: 20,
          bottom: 20,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildShoulderButtons(true),
              _buildJoystick(true),
            ],
          ),
        ),
        
        // Center controls
        Positioned(
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          child: Center(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildDPad(),
                const SizedBox(width: 100),
                _buildActionButtons(),
              ],
            ),
          ),
        ),
        
        // Right side controls
        Positioned(
          right: 20,
          top: 20,
          bottom: 20,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildShoulderButtons(false),
              _buildJoystick(false),
            ],
          ),
        ),
        
        // Middle buttons
        Positioned(
          left: 0,
          right: 0,
          bottom: 20,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildSmallButton('SELECT', Icons.select_all),
              const SizedBox(width: 40),
              _buildSmallButton('START', Icons.play_arrow),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPortraitLayout() {
    return Column(
      children: [
        _buildShoulderButtonsRow(),
        Expanded(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _buildDPad(),
                    const SizedBox(height: 20),
                    _buildJoystick(true),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _buildActionButtons(),
                    const SizedBox(height: 20),
                    _buildJoystick(false),
                  ],
                ),
              ),
            ],
          ),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildSmallButton('SELECT', Icons.select_all),
            const SizedBox(width: 40),
            _buildSmallButton('START', Icons.play_arrow),
          ],
        ),
        const SizedBox(height: 20),
      ],
    );
  }

  Widget _buildShoulderButtonsRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _buildShoulderButtons(true),
          _buildShoulderButtons(false),
        ],
      ),
    );
  }

  Widget _buildShoulderButtons(bool isLeft) {
    return Column(
      children: [
        _buildButton(
          isLeft ? 'L1' : 'R1',
          60,
          30,
        ),
        const SizedBox(height: 4),
        _buildButton(
          isLeft ? 'L2' : 'R2',
          60,
          30,
        ),
      ],
    );
  }

  Widget _buildDPad() {
    return SizedBox(
      width: 120,
      height: 120,
      child: Stack(
        children: [
          Positioned(
            top: 0,
            left: 40,
            child: _buildDPadButton('UP', Icons.arrow_drop_up, 40, 40),
          ),
          Positioned(
            bottom: 0,
            left: 40,
            child: _buildDPadButton('DOWN', Icons.arrow_drop_down, 40, 40),
          ),
          Positioned(
            left: 0,
            top: 40,
            child: _buildDPadButton('LEFT', Icons.arrow_left, 40, 40),
          ),
          Positioned(
            right: 0,
            top: 40,
            child: _buildDPadButton('RIGHT', Icons.arrow_right, 40, 40),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return SizedBox(
      width: 120,
      height: 120,
      child: Stack(
        children: [
          Positioned(
            top: 0,
            left: 40,
            child: _buildCircleButton('Y', Colors.yellow),
          ),
          Positioned(
            bottom: 0,
            left: 40,
            child: _buildCircleButton('A', Colors.green),
          ),
          Positioned(
            left: 0,
            top: 40,
            child: _buildCircleButton('X', Colors.blue),
          ),
          Positioned(
            right: 0,
            top: 40,
            child: _buildCircleButton('B', Colors.red),
          ),
        ],
      ),
    );
  }

  Widget _buildJoystick(bool isLeft) {
    return GestureDetector(
      onPanStart: (_) {},
      onPanUpdate: (details) {
        _handleJoystickMove(details.localPosition, isLeft);
      },
      onPanEnd: (_) {
        _handleJoystickRelease(isLeft);
      },
      child: Container(
        width: 100,
        height: 100,
        decoration: BoxDecoration(
          color: Colors.grey[800],
          shape: BoxShape.circle,
          border: Border.all(color: Colors.blue, width: 2),
        ),
        child: Stack(
          children: [
            Positioned(
              left: 50 + (isLeft ? _leftStickOffset.dx : _rightStickOffset.dx) * 30 - 15,
              top: 50 + (isLeft ? _leftStickOffset.dy : _rightStickOffset.dy) * 30 - 15,
              child: Container(
                width: 30,
                height: 30,
                decoration: const BoxDecoration(
                  color: Colors.blue,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _handleJoystickMove(Offset position, bool isLeft) {
    final center = const Offset(50, 50);
    final delta = position - center;
    final distance = delta.distance;
    
    Offset normalized;
    if (distance > 30) {
      normalized = delta / distance;
    } else {
      normalized = delta / 30;
    }
    
    setState(() {
      if (isLeft) {
        _leftStickOffset = normalized;
      } else {
        _rightStickOffset = normalized;
      }
    });
    
    _gamepadController.sendJoystick(
      isLeft ? 'left' : 'right',
      normalized.dx,
      -normalized.dy,
    );
  }

  void _handleJoystickRelease(bool isLeft) {
    setState(() {
      if (isLeft) {
        _leftStickOffset = Offset.zero;
      } else {
        _rightStickOffset = Offset.zero;
      }
    });
    
    _gamepadController.sendJoystick(
      isLeft ? 'left' : 'right',
      0,
      0,
    );
  }

  Widget _buildCircleButton(String label, Color color) {
    return GestureDetector(
      onTapDown: (_) => _gamepadController.sendButton(label, true),
      onTapUp: (_) => _gamepadController.sendButton(label, false),
      onTapCancel: () => _gamepadController.sendButton(label, false),
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: color.withOpacity(0.3),
          shape: BoxShape.circle,
          border: Border.all(color: color, width: 2),
        ),
        child: Center(
          child: Text(
            label,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildButton(String label, double width, double height) {
    return GestureDetector(
      onTapDown: (_) => _gamepadController.sendButton(label, true),
      onTapUp: (_) => _gamepadController.sendButton(label, false),
      onTapCancel: () => _gamepadController.sendButton(label, false),
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: Colors.grey[800],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.blue, width: 2),
        ),
        child: Center(
          child: Text(
            label,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDPadButton(String direction, IconData icon, double width, double height) {
    return GestureDetector(
      onTapDown: (_) => _gamepadController.sendDPad(direction, true),
      onTapUp: (_) => _gamepadController.sendDPad(direction, false),
      onTapCancel: () => _gamepadController.sendDPad(direction, false),
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: Colors.grey[800],
          border: Border.all(color: Colors.blue, width: 2),
        ),
        child: Icon(icon, color: Colors.blue),
      ),
    );
  }

  Widget _buildSmallButton(String label, IconData icon) {
    return GestureDetector(
      onTap: () => _gamepadController.sendButton(label, true),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.grey[800],
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.blue, width: 2),
        ),
        child: Row(
          children: [
            Icon(icon, size: 16),
            const SizedBox(width: 4),
            Text(label, style: const TextStyle(fontSize: 12)),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _stopGyro();
    _gamepadController.dispose();
    super.dispose();
  }
}