import 'package:flutter/material.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/touchpad_controller.dart';

class TouchpadScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const TouchpadScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<TouchpadScreen> createState() => _TouchpadScreenState();
}

class _TouchpadScreenState extends State<TouchpadScreen> {
  late TouchpadController _touchpadController;
  double _sensitivity = 1.0;
  double _scrollValue = 0.0;

  @override
  void initState() {
    super.initState();
    _touchpadController = TouchpadController(widget.connectionManager);
    _touchpadController.setSensitivity(_sensitivity);
  }

  @override
  Widget build(BuildContext context) {
    final isLandscape = MediaQuery.of(context).orientation == Orientation.landscape;
    
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('Touchpad'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSensitivityDialog,
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

  Widget _buildPortraitLayout() {
    return Column(
      children: [
        // Sensitivity control
        _buildSensitivityControl(),
        
        // Main touchpad area
        Expanded(
          child: Row(
            children: [
              // Touchpad area
              Expanded(
                child: _buildTouchpadArea(),
              ),
              
              // Scrollbar on the right
              _buildScrollbar(),
            ],
          ),
        ),
        
        // Click buttons at bottom
        _buildClickButtons(),
      ],
    );
  }

  Widget _buildLandscapeLayout() {
    return Row(
      children: [
        // Main touchpad area
        Expanded(
          child: Column(
            children: [
              // Sensitivity control
              _buildSensitivityControl(),
              
              // Touchpad area
              Expanded(
                child: _buildTouchpadArea(),
              ),
              
              // Click buttons at bottom
              _buildClickButtons(),
            ],
          ),
        ),
        
        // Scrollbar on the right
        _buildScrollbar(),
      ],
    );
  }

  Widget _buildSensitivityControl() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        border: Border(
          bottom: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.speed, size: 20, color: Colors.blue),
          const SizedBox(width: 12),
          const Text(
            'Sensitivity:',
            style: TextStyle(fontSize: 14),
          ),
          Expanded(
            child: Slider(
              value: _sensitivity,
              min: 0.5,
              max: 3.0,
              divisions: 10,
              label: _sensitivity.toStringAsFixed(1),
              onChanged: (value) {
                setState(() {
                  _sensitivity = value;
                  _touchpadController.setSensitivity(value);
                });
              },
            ),
          ),
          Text(
            _sensitivity.toStringAsFixed(1),
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),
          const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _buildTouchpadArea() {
    return GestureDetector(
      onPanStart: _touchpadController.handlePanStart,
      onPanUpdate: _touchpadController.handlePanUpdate,
      onTap: _touchpadController.handleTap,
      onDoubleTap: _touchpadController.handleDoubleTap,
      child: Container(
        margin: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey[900],
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.blue, width: 2),
          boxShadow: [
            BoxShadow(
              color: Colors.blue.withOpacity(0.2),
              blurRadius: 10,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.touch_app,
                size: 64,
                color: Colors.grey[700],
              ),
              const SizedBox(height: 16),
              Text(
                'Touchpad Area',
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Text(
                  'Drag to move cursor\nTap to click\nDouble-tap for double-click',
                  style: TextStyle(
                    color: Colors.grey[700],
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildScrollbar() {
    return Container(
      width: 60,
      margin: const EdgeInsets.only(right: 16, top: 16, bottom: 16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: Colors.blue, width: 2),
      ),
      child: GestureDetector(
        onVerticalDragUpdate: (details) {
          // Scroll based on drag
          final delta = details.primaryDelta ?? 0.0;
          _touchpadController.handleScroll(0, -delta);
        },
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.arrow_upward,
              color: Colors.grey[600],
              size: 24,
            ),
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  border: Border(
                    left: BorderSide(color: Colors.blue.withOpacity(0.5), width: 2),
                  ),
                ),
                child: Center(
                  child: RotatedBox(
                    quarterTurns: 3,
                    child: Text(
                      'SCROLL',
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 10,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            Icon(
              Icons.arrow_downward,
              color: Colors.grey[600],
              size: 24,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildClickButtons() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        border: Border(
          top: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildClickButton(
              'Left Click',
              Icons.touch_app,
              Colors.blue,
              _touchpadController.leftClick,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildClickButton(
              'Middle',
              Icons.adjust,
              Colors.purple,
              _touchpadController.middleClick,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildClickButton(
              'Right Click',
              Icons.menu,
              Colors.orange,
              _touchpadController.rightClick,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClickButton(String label, IconData icon, Color color, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.2),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color, width: 2),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showSensitivityDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Touchpad Settings'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Adjust cursor sensitivity:'),
            const SizedBox(height: 16),
            Slider(
              value: _sensitivity,
              min: 0.5,
              max: 3.0,
              divisions: 10,
              label: _sensitivity.toStringAsFixed(1),
              onChanged: (value) {
                setState(() {
                  _sensitivity = value;
                  _touchpadController.setSensitivity(value);
                });
              },
            ),
            Text(
              'Current: ${_sensitivity.toStringAsFixed(1)}x',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _touchpadController.dispose();
    super.dispose();
  }
}
