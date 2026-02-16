import 'package:flutter/material.dart';
import '../core/connection_manager.dart';

class TouchpadController {
  final ConnectionManager connectionManager;
  
  Offset _lastPosition = Offset.zero;
  double _sensitivity = 1.0;
  
  TouchpadController(this.connectionManager);
  
  void setSensitivity(double sensitivity) {
    _sensitivity = sensitivity;
  }
  
  void handlePanStart(DragStartDetails details) {
    _lastPosition = details.localPosition;
  }
  
  void handlePanUpdate(DragUpdateDetails details) {
    final delta = details.localPosition - _lastPosition;
    _lastPosition = details.localPosition;
    
    // Apply sensitivity
    final dx = (delta.dx * _sensitivity).round();
    final dy = (delta.dy * _sensitivity).round();
    
    if (dx != 0 || dy != 0) {
      connectionManager.sendMessage({
        'type': 'mouse',
        'action': 'move_relative',
        'dx': dx,
        'dy': dy,
      });
    }
  }
  
  void handleTap() {
    // Single tap = left click
    connectionManager.sendMessage({
      'type': 'mouse',
      'action': 'click',
      'button': 'left',
      'count': 1,
    });
  }
  
  void handleDoubleTap() {
    // Double tap = double left click
    connectionManager.sendMessage({
      'type': 'mouse',
      'action': 'click',
      'button': 'left',
      'count': 2,
    });
  }
  
  void handleTwoFingerTap() {
    // Two finger tap = right click
    connectionManager.sendMessage({
      'type': 'mouse',
      'action': 'click',
      'button': 'right',
      'count': 1,
    });
  }
  
  void handleScroll(double dx, double dy) {
    connectionManager.sendMessage({
      'type': 'mouse',
      'action': 'scroll',
      'dx': dx.round(),
      'dy': dy.round(),
    });
  }
  
  void leftClick() {
    connectionManager.sendMessage({
      'type': 'mouse',
      'action': 'click',
      'button': 'left',
      'count': 1,
    });
  }
  
  void rightClick() {
    connectionManager.sendMessage({
      'type': 'mouse',
      'action': 'click',
      'button': 'right',
      'count': 1,
    });
  }
  
  void middleClick() {
    connectionManager.sendMessage({
      'type': 'mouse',
      'action': 'click',
      'button': 'middle',
      'count': 1,
    });
  }
  
  void dispose() {
    // Cleanup if needed
  }
}

class TouchpadWidget extends StatefulWidget {
  final TouchpadController controller;
  
  const TouchpadWidget({
    Key? key,
    required this.controller,
  }) : super(key: key);
  
  @override
  State<TouchpadWidget> createState() => _TouchpadWidgetState();
}

class _TouchpadWidgetState extends State<TouchpadWidget> {
  int _touchCount = 0;
  
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onPanStart: widget.controller.handlePanStart,
      onPanUpdate: widget.controller.handlePanUpdate,
      onTap: widget.controller.handleTap,
      onDoubleTap: widget.controller.handleDoubleTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.grey[900],
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.blue, width: 2),
        ),
        child: Stack(
          children: [
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.touch_app,
                    size: 48,
                    color: Colors.grey[600],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Touchpad',
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Tap to click • Two fingers to right-click • Drag to move',
                    style: TextStyle(
                      color: Colors.grey[700],
                      fontSize: 12,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
            
            // Mouse buttons at bottom
            Positioned(
              left: 16,
              right: 16,
              bottom: 16,
              child: Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      onPressed: widget.controller.leftClick,
                      child: const Text('L'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: widget.controller.middleClick,
                      child: const Text('M'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: widget.controller.rightClick,
                      child: const Text('R'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}