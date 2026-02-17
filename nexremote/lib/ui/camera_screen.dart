import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:typed_data';
import '../core/connection_manager.dart';
import '../input/camera_controller.dart';

class CameraScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const CameraScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  late CameraController _cameraController;
  Uint8List? _currentFrame;
  List<Map<String, dynamic>> _cameras = [];
  int _selectedCameraIndex = 0;
  bool _isStreaming = false;
  bool _isLoading = true;
  Map<String, dynamic>? _cameraInfo;
  DateTime? _lastFrameTime;
  double _currentFps = 0.0;

  StreamSubscription? _frameSub;
  StreamSubscription? _cameraListSub;
  StreamSubscription? _cameraInfoSub;

  @override
  void initState() {
    super.initState();
    _cameraController = CameraController(widget.connectionManager);

    // Listen for frames
    _frameSub = _cameraController.frameStream.listen((bytes) {
      setState(() {
        _currentFrame = bytes;
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

    // Listen for camera list
    _cameraListSub = _cameraController.cameraListStream.listen((cameras) {
      setState(() {
        _cameras = cameras;
        _isLoading = false;
      });
    });

    // Listen for camera info
    _cameraInfoSub = _cameraController.cameraInfoStream.listen((info) {
      setState(() {
        _cameraInfo = info;
      });
    });

    // Request camera list
    _cameraController.requestCameraList();
  }

  void _toggleStreaming() {
    if (_isStreaming) {
      _stopStreaming();
    } else {
      _startStreaming();
    }
  }

  void _startStreaming() {
    if (_cameras.isEmpty) {
      _showError('No cameras available');
      return;
    }

    setState(() {
      _isStreaming = true;
    });

    _cameraController.startStreaming(cameraIndex: _selectedCameraIndex);
  }

  void _stopStreaming() {
    _cameraController.stopStreaming();

    setState(() {
      _isStreaming = false;
      _currentFrame = null;
      _currentFps = 0.0;
    });
  }

  void _switchCamera(int index) {
    if (index == _selectedCameraIndex) return;

    setState(() {
      _selectedCameraIndex = index;
    });

    if (_isStreaming) {
      _cameraController.setCamera(index);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('Camera'),
        actions: [
          if (_cameras.length > 1)
            PopupMenuButton<int>(
              icon: const Icon(Icons.switch_camera),
              onSelected: _switchCamera,
              itemBuilder: (context) => List.generate(
                _cameras.length,
                (index) => PopupMenuItem(
                  value: index,
                  child: Row(
                    children: [
                      const Icon(Icons.videocam),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _cameras[index]['name'] ?? 'Camera $index',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (index == _selectedCameraIndex)
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
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() => _isLoading = true);
              _cameraController.requestCameraList();
            },
            tooltip: 'Refresh cameras',
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Camera preview
            Expanded(
              child: _buildCameraPreview(),
            ),

            // Controls
            _buildControls(),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraPreview() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_cameras.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.videocam_off, size: 100, color: Colors.grey[600]),
            const SizedBox(height: 24),
            Text(
              'No cameras found on PC',
              style: TextStyle(fontSize: 18, color: Colors.grey[400]),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: () {
                setState(() => _isLoading = true);
                _cameraController.requestCameraList();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (!_isStreaming || _currentFrame == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.videocam, size: 100, color: Colors.grey[600]),
            const SizedBox(height: 24),
            Text(
              _isStreaming ? 'Waiting for frames...' : 'Camera ready',
              style: TextStyle(fontSize: 18, color: Colors.grey[400]),
            ),
            if (_cameras.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                _cameras[_selectedCameraIndex]['name'] ?? 'Camera $_selectedCameraIndex',
                style: TextStyle(fontSize: 14, color: Colors.grey[500]),
              ),
            ],
          ],
        ),
      );
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        // Camera feed
        Container(
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.green, width: 3),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(9),
            child: Image.memory(
              _currentFrame!,
              fit: BoxFit.contain,
              gaplessPlayback: true, // Prevents flicker between frames
            ),
          ),
        ),

        // Streaming indicator
        Positioned(
          top: 30,
          left: 30,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.red,
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.fiber_manual_record, size: 12, color: Colors.white),
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

        // FPS and info overlay
        Positioned(
          top: 30,
          right: 30,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.black54,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '${_currentFps.toStringAsFixed(1)} FPS',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
        ),

        // Resolution info
        if (_cameraInfo != null)
          Positioned(
            bottom: 30,
            left: 30,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                '${_cameraInfo!['width'] ?? '?'}×${_cameraInfo!['height'] ?? '?'} @ ${_cameraInfo!['fps'] ?? '?'} fps',
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
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
          // Camera selector
          if (_cameras.length > 1)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  const Icon(Icons.videocam, size: 20, color: Colors.blue),
                  const SizedBox(width: 12),
                  const Text('Camera:', style: TextStyle(color: Colors.white)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButton<int>(
                      value: _selectedCameraIndex,
                      isExpanded: true,
                      dropdownColor: Colors.grey[800],
                      items: List.generate(
                        _cameras.length,
                        (i) => DropdownMenuItem(
                          value: i,
                          child: Text(
                            _cameras[i]['name'] ?? 'Camera $i',
                            style: const TextStyle(color: Colors.white),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                      onChanged: (val) {
                        if (val != null) _switchCamera(val);
                      },
                    ),
                  ),
                ],
              ),
            ),

          // Camera native info
          if (_cameraInfo != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, size: 20, color: Colors.blue),
                  const SizedBox(width: 12),
                  Text(
                    'Native: ${_cameraInfo!['width']}×${_cameraInfo!['height']} @ ${_cameraInfo!['fps']} fps',
                    style: TextStyle(color: Colors.grey[400], fontSize: 13),
                  ),
                ],
              ),
            ),

          // Start/Stop button
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              onPressed: _cameras.isEmpty ? null : _toggleStreaming,
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

  @override
  void dispose() {
    _frameSub?.cancel();
    _cameraListSub?.cancel();
    _cameraInfoSub?.cancel();
    _cameraController.dispose();
    super.dispose();
  }
}
