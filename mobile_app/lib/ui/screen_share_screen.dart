import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:typed_data';
import '../core/connection_manager.dart';
import '../input/screen_share_controller.dart';

class ScreenShareScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const ScreenShareScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<ScreenShareScreen> createState() => _ScreenShareScreenState();
}

class _ScreenShareScreenState extends State<ScreenShareScreen> {
  late ScreenShareController _controller;
  Uint8List? _currentFrame;
  List<Map<String, dynamic>> _displays = [];
  int _selectedDisplay = 0;
  bool _isStreaming = false;
  int _fps = 10;
  String _quality = 'medium';
  double _scale = 1.0;
  int _frameCount = 0;
  DateTime? _lastFrameTime;
  double _currentFps = 0.0;

  @override
  void initState() {
    super.initState();
    _controller = ScreenShareController(widget.connectionManager);
    
    _controller.frameStream.listen((bytes) {
      setState(() {
        _currentFrame = bytes;
        _frameCount++;
        
        // Calculate actual FPS
        final now = DateTime.now();
        if (_lastFrameTime != null) {
          final diff = now.difference(_lastFrameTime!).inMilliseconds;
          if (diff > 0) {
            _currentFps = 1000 / diff;
          }
        }
        _lastFrameTime = now;
      });
    });

    _controller.displaysStream.listen((displays) {
      setState(() {
        _displays = displays;
      });
    });

    _controller.requestDisplayList();
  }

  void _toggleStreaming() {
    if (_isStreaming) {
      _stopStreaming();
    } else {
      _startStreaming();
    }
  }

  void _startStreaming() {
    setState(() {
      _isStreaming = true;
      _frameCount = 0;
    });

    _controller.startStreaming(
      displayIndex: _selectedDisplay,
      fps: _fps,
      quality: _quality,
    );
  }

  void _stopStreaming() {
    setState(() {
      _isStreaming = false;
      _currentFps = 0.0;
    });

    _controller.stopStreaming();
  }

  void _changeDisplay(int index) {
    if (index == _selectedDisplay) return;

    final wasStreaming = _isStreaming;
    if (wasStreaming) {
      _stopStreaming();
    }

    setState(() {
      _selectedDisplay = index;
    });

    if (wasStreaming) {
      Future.delayed(const Duration(milliseconds: 100), () {
        _startStreaming();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('Screen Share'),
        actions: [
          if (_displays.length > 1)
            PopupMenuButton<int>(
              icon: const Icon(Icons.monitor),
              onSelected: _changeDisplay,
              itemBuilder: (context) => List.generate(
                _displays.length,
                (index) => PopupMenuItem(
                  value: index,
                  child: Row(
                    children: [
                      const Icon(Icons.desktop_windows),
                      const SizedBox(width: 8),
                      Text('Display ${index + 1}'),
                      if (index == _selectedDisplay)
                        const Padding(
                          padding: EdgeInsets.only(left: 8),
                          child: Icon(Icons.check, color: Colors.blue),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSettings,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Screen display
            Expanded(
              child: _buildScreenDisplay(),
            ),

            // Controls
            _buildControls(),
          ],
        ),
      ),
    );
  }

  Widget _buildScreenDisplay() {
    if (!_isStreaming && _currentFrame == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.screen_share,
              size: 100,
              color: Colors.grey[600],
            ),
            const SizedBox(height: 24),
            Text(
              'Not Streaming',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.grey[400],
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Tap "Start Streaming" to view PC screen',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey[500],
              ),
            ),
          ],
        ),
      );
    }

    if (_currentFrame == null) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Waiting for frames...'),
          ],
        ),
      );
    }

    return Stack(
      children: [
        // Screen image with pinch-to-zoom
        InteractiveViewer(
          minScale: 0.5,
          maxScale: 4.0,
          onInteractionUpdate: (details) {
            setState(() {
              _scale = details.scale;
            });
          },
          child: Container(
            margin: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _isStreaming ? Colors.green : Colors.blue,
                width: 3,
              ),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(9),
              child: Image.memory(
                _currentFrame!,
                fit: BoxFit.contain,
                gaplessPlayback: true,
              ),
            ),
          ),
        ),

        // Streaming indicator
        if (_isStreaming)
          Positioned(
            top: 30,
            left: 30,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.green,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: const [
                  Icon(Icons.circle, size: 12, color: Colors.white),
                  SizedBox(width: 6),
                  Text(
                    'LIVE',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),

        // FPS and quality indicator
        if (_isStreaming)
          Positioned(
            top: 30,
            right: 30,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${_currentFps.toStringAsFixed(1)} FPS',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                  Text(
                    _quality.toUpperCase(),
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),
          ),

        // Zoom indicator
        if (_scale != 1.0)
          Positioned(
            bottom: 30,
            right: 30,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                '${(_scale * 100).toStringAsFixed(0)}%',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildControls() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        border: Border(
          top: BorderSide(color: Colors.blue.withOpacity(0.3), width: 1),
        ),
      ),
      child: Column(
        children: [
          // FPS control
          Row(
            children: [
              const Icon(Icons.speed, size: 20, color: Colors.blue),
              const SizedBox(width: 12),
              const Text('FPS:'),
              Expanded(
                child: Slider(
                  value: _fps.toDouble(),
                  min: 5,
                  max: 30,
                  divisions: 5,
                  label: '$_fps',
                  onChanged: _isStreaming
                      ? null
                      : (value) {
                          setState(() {
                            _fps = value.round();
                          });
                        },
                ),
              ),
              Text('$_fps'),
              const SizedBox(width: 8),
            ],
          ),

          const SizedBox(height: 8),

          // Start/Stop button
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              onPressed: _toggleStreaming,
              icon: Icon(_isStreaming ? Icons.stop : Icons.play_arrow),
              label: Text(
                _isStreaming ? 'Stop Streaming' : 'Start Streaming',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: _isStreaming ? Colors.red : Colors.green,
                foregroundColor: Colors.white,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showSettings() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Screen Share Settings'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Quality:', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'low', label: Text('Low')),
                ButtonSegment(value: 'medium', label: Text('Medium')),
                ButtonSegment(value: 'high', label: Text('High')),
              ],
              selected: {_quality},
              onSelectionChanged: (Set<String> selected) {
                if (!_isStreaming) {
                  setState(() {
                    _quality = selected.first;
                  });
                }
              },
            ),
            const SizedBox(height: 16),
            Text(
              'Frames received: $_frameCount',
              style: TextStyle(color: Colors.grey[600]),
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
    _controller.dispose();
    super.dispose();
  }
}
