import 'package:flutter/material.dart';
import 'layout_manager.dart';
import '../input/gamepad_controller.dart';

class LayoutWidget extends StatelessWidget {
  final GamepadLayout layout;
  final GamepadController gamepadController;
  
  const LayoutWidget({
    Key? key,
    required this.layout,
    required this.gamepadController,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    
    return Stack(
      children: layout.elements.map((element) {
        return _buildElement(element, size);
      }).toList(),
    );
  }
  
  Widget _buildElement(LayoutElement element, Size screenSize) {
    final left = element.position['x']! * screenSize.width;
    final top = element.position['y']! * screenSize.height;
    
    Widget child;
    
    switch (element.type) {
      case 'button':
        child = _buildButton(element);
        break;
      case 'joystick':
        child = _buildJoystick(element);
        break;
      case 'dpad':
        child = _buildDPad(element);
        break;
      case 'face_buttons':
        child = _buildFaceButtons(element);
        break;
      case 'trigger':
        child = _buildTrigger(element);
        break;
      default:
        child = Container();
    }
    
    return Positioned(
      left: left,
      top: top,
      child: child,
    );
  }
  
  Widget _buildButton(LayoutElement element) {
    final width = (element.size as Map)['width']?.toDouble() ?? 60.0;
    final height = (element.size as Map)['height']?.toDouble() ?? 60.0;
    
    return GestureDetector(
      onTapDown: (_) => _handleButtonPress(element.action ?? element.label ?? ''),
      onTapUp: (_) => _handleButtonRelease(element.action ?? element.label ?? ''),
      onTapCancel: () => _handleButtonRelease(element.action ?? element.label ?? ''),
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
            element.label ?? '',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildJoystick(LayoutElement element) {
    final size = element.size is int 
        ? (element.size as int).toDouble() 
        : 100.0;
    
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: Colors.grey[800],
        shape: BoxShape.circle,
        border: Border.all(color: Colors.blue, width: 2),
      ),
      // Joystick logic would be implemented here
      // For now, this is a placeholder
    );
  }
  
  Widget _buildDPad(LayoutElement element) {
    final size = element.size is int 
        ? (element.size as int).toDouble() 
        : 120.0;
    
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          // Up
          Positioned(
            top: 0,
            left: size / 3,
            child: _buildDPadButton('UP', size / 3),
          ),
          // Down
          Positioned(
            bottom: 0,
            left: size / 3,
            child: _buildDPadButton('DOWN', size / 3),
          ),
          // Left
          Positioned(
            left: 0,
            top: size / 3,
            child: _buildDPadButton('LEFT', size / 3),
          ),
          // Right
          Positioned(
            right: 0,
            top: size / 3,
            child: _buildDPadButton('RIGHT', size / 3),
          ),
        ],
      ),
    );
  }
  
  Widget _buildDPadButton(String direction, double size) {
    return GestureDetector(
      onTapDown: (_) => gamepadController.sendDPad(direction, true),
      onTapUp: (_) => gamepadController.sendDPad(direction, false),
      onTapCancel: () => gamepadController.sendDPad(direction, false),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: Colors.grey[800],
          border: Border.all(color: Colors.blue, width: 2),
        ),
        child: Icon(
          _getDPadIcon(direction),
          color: Colors.blue,
        ),
      ),
    );
  }
  
  IconData _getDPadIcon(String direction) {
    switch (direction) {
      case 'UP':
        return Icons.arrow_drop_up;
      case 'DOWN':
        return Icons.arrow_drop_down;
      case 'LEFT':
        return Icons.arrow_left;
      case 'RIGHT':
        return Icons.arrow_right;
      default:
        return Icons.circle;
    }
  }
  
  Widget _buildFaceButtons(LayoutElement element) {
    final size = element.size is int 
        ? (element.size as int).toDouble() 
        : 120.0;
    
    final buttonSize = size / 3;
    
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          // Y (top)
          Positioned(
            top: 0,
            left: buttonSize,
            child: _buildFaceButton('Y', Colors.yellow, buttonSize),
          ),
          // A (bottom)
          Positioned(
            bottom: 0,
            left: buttonSize,
            child: _buildFaceButton('A', Colors.green, buttonSize),
          ),
          // X (left)
          Positioned(
            left: 0,
            top: buttonSize,
            child: _buildFaceButton('X', Colors.blue, buttonSize),
          ),
          // B (right)
          Positioned(
            right: 0,
            top: buttonSize,
            child: _buildFaceButton('B', Colors.red, buttonSize),
          ),
        ],
      ),
    );
  }
  
  Widget _buildFaceButton(String label, Color color, double size) {
    return GestureDetector(
      onTapDown: (_) => gamepadController.sendButton(label, true),
      onTapUp: (_) => gamepadController.sendButton(label, false),
      onTapCancel: () => gamepadController.sendButton(label, false),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color.withOpacity(0.3),
          shape: BoxShape.circle,
          border: Border.all(color: color, width: 2),
        ),
        child: Center(
          child: Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildTrigger(LayoutElement element) {
    final width = (element.size as Map)['width']?.toDouble() ?? 60.0;
    final height = (element.size as Map)['height']?.toDouble() ?? 30.0;
    
    return GestureDetector(
      onTapDown: (_) => gamepadController.sendButton(element.trigger ?? '', true),
      onTapUp: (_) => gamepadController.sendButton(element.trigger ?? '', false),
      onTapCancel: () => gamepadController.sendButton(element.trigger ?? '', false),
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
            element.label ?? '',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }
  
  void _handleButtonPress(String action) {
    if (action.startsWith('keyboard_')) {
      // Keyboard action
      final key = action.substring(9);
      gamepadController.sendButton(key, true);
    } else if (action.startsWith('mouse_')) {
      // Mouse action
      final button = action.substring(6);
      gamepadController.sendButton(button, true);
    } else {
      // Gamepad button
      gamepadController.sendButton(action, true);
    }
  }
  
  void _handleButtonRelease(String action) {
    if (action.startsWith('keyboard_')) {
      final key = action.substring(9);
      gamepadController.sendButton(key, false);
    } else if (action.startsWith('mouse_')) {
      final button = action.substring(6);
      gamepadController.sendButton(button, false);
    } else {
      gamepadController.sendButton(action, false);
    }
  }
}