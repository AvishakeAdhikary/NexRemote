import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:typed_data';
import '../core/connection_manager.dart';
import '../input/camera_controller.dart';

class CameraScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const CameraScreen({super.key, required this.connectionManager});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  late CameraController _cameraController;
  List<Map<String, dynamic>> _cameras = [];
  bool _isLoading = true;
  Timer? _loadingTimeoutTimer;

  // Multi-stream state
  final Map<int, Uint8List?> _frames = {};
  final Map<int, double> _fpsMap = {};
  final Map<int, DateTime> _lastFrameTimeMap = {};
  final Map<int, StreamSubscription> _frameSubs = {};
  final Set<int> _selectedCameras = {};
  bool _isStreaming = false;

  // Legacy single-stream
  StreamSubscription? _cameraListSub;
  StreamSubscription? _cameraInfoSub;

  @override
  void initState() {
    super.initState();
    _cameraController = CameraController(widget.connectionManager);

    _cameraListSub = _cameraController.cameraListStream.listen((cameras) {
      if (mounted) {
        setState(() {
          _cameras = cameras;
          _isLoading = false;
          // Pre-select first camera
          if (_selectedCameras.isEmpty && cameras.isNotEmpty) {
            _selectedCameras.add(cameras[0]['index'] as int);
          }
        });
      }
    });

    _cameraInfoSub = _cameraController.cameraInfoStream.listen((info) {
      // Camera info handled per-stream in multi-camera mode
    });

    _requestCameraList();
  }

  void _requestCameraList() {
    setState(() => _isLoading = true);
    _cameraController.requestCameraList();
    _loadingTimeoutTimer?.cancel();
    _loadingTimeoutTimer = Timer(const Duration(seconds: 5), () {
      if (mounted && _isLoading) setState(() => _isLoading = false);
    });
  }

  void _toggleCameraSelection(int index) {
    setState(() {
      if (_selectedCameras.contains(index)) {
        _selectedCameras.remove(index);
      } else {
        _selectedCameras.add(index);
      }
    });
  }

  void _startStreaming() {
    if (_selectedCameras.isEmpty) {
      _showError('Select at least one camera');
      return;
    }

    setState(() => _isStreaming = true);

    // Subscribe to per-camera frame streams
    for (final camIdx in _selectedCameras) {
      _frameSubs[camIdx]?.cancel();
      _frameSubs[camIdx] = _cameraController.frameStreamFor(camIdx).listen((
        bytes,
      ) {
        if (mounted) {
          setState(() {
            _frames[camIdx] = bytes;
            final now = DateTime.now();
            final last = _lastFrameTimeMap[camIdx];
            if (last != null) {
              final diff = now.difference(last).inMilliseconds;
              if (diff > 0) _fpsMap[camIdx] = 1000 / diff;
            }
            _lastFrameTimeMap[camIdx] = now;
          });
        }
      });
    }

    if (_selectedCameras.length == 1) {
      _cameraController.startStreaming(cameraIndex: _selectedCameras.first);
    } else {
      _cameraController.startMultiStreaming(_selectedCameras.toList());
    }
  }

  void _stopStreaming() {
    _cameraController.stopStreaming();
    for (final sub in _frameSubs.values) {
      sub.cancel();
    }
    _frameSubs.clear();

    setState(() {
      _isStreaming = false;
      _frames.clear();
      _fpsMap.clear();
      _lastFrameTimeMap.clear();
    });
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('Camera'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _requestCameraList,
            tooltip: 'Refresh cameras',
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(child: _buildPreview()),
            _buildControls(),
          ],
        ),
      ),
    );
  }

  Widget _buildPreview() {
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
              onPressed: _requestCameraList,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (!_isStreaming) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.videocam, size: 100, color: Colors.grey[600]),
            const SizedBox(height: 24),
            Text(
              'Select cameras and press Start',
              style: TextStyle(fontSize: 18, color: Colors.grey[400]),
            ),
          ],
        ),
      );
    }

    // Active streams grid
    final activeIndices = _selectedCameras
        .where((i) => _frames.containsKey(i))
        .toList();
    if (activeIndices.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(
              'Waiting for frames...',
              style: TextStyle(color: Colors.white54),
            ),
          ],
        ),
      );
    }

    if (activeIndices.length == 1) {
      return _buildSingleFeed(activeIndices[0]);
    }

    // Grid for multiple cameras
    final crossCount = activeIndices.length <= 2 ? 1 : 2;
    return GridView.builder(
      padding: const EdgeInsets.all(8),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossCount,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
        childAspectRatio: 16 / 9,
      ),
      itemCount: activeIndices.length,
      itemBuilder: (_, i) => _buildGridFeed(activeIndices[i]),
    );
  }

  Widget _buildSingleFeed(int camIdx) {
    final frame = _frames[camIdx];
    if (frame == null) return const SizedBox.shrink();

    return Stack(
      fit: StackFit.expand,
      children: [
        Container(
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.green, width: 3),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(9),
            child: Image.memory(
              frame,
              fit: BoxFit.contain,
              gaplessPlayback: true,
            ),
          ),
        ),
        _buildLiveIndicator(),
        _buildFpsOverlay(camIdx),
      ],
    );
  }

  Widget _buildGridFeed(int camIdx) {
    final frame = _frames[camIdx];
    final camName =
        _cameras.firstWhere(
              (c) => c['index'] == camIdx,
              orElse: () => {'name': 'Camera $camIdx'},
            )['name']
            as String;

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.green, width: 2),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (frame != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: Image.memory(
                frame,
                fit: BoxFit.contain,
                gaplessPlayback: true,
              ),
            )
          else
            const Center(child: CircularProgressIndicator(strokeWidth: 2)),
          // Camera label
          Positioned(
            top: 6,
            left: 6,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                camName,
                style: const TextStyle(color: Colors.white, fontSize: 11),
              ),
            ),
          ),
          // FPS
          Positioned(
            top: 6,
            right: 6,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${(_fpsMap[camIdx] ?? 0).toStringAsFixed(0)} FPS',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLiveIndicator() {
    return Positioned(
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
    );
  }

  Widget _buildFpsOverlay(int camIdx) {
    return Positioned(
      top: 30,
      right: 30,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.black54,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          '${(_fpsMap[camIdx] ?? 0).toStringAsFixed(1)} FPS',
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            fontSize: 12,
          ),
        ),
      ),
    );
  }

  Widget _buildControls() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        border: Border(
          top: BorderSide(color: Colors.blue.withValues(alpha: 0.3), width: 1),
        ),
      ),
      child: Column(
        children: [
          // Camera selector chips (multi-select)
          if (_cameras.isNotEmpty && !_isStreaming)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _cameras.map((cam) {
                  final idx = cam['index'] as int;
                  final selected = _selectedCameras.contains(idx);
                  return FilterChip(
                    label: Text(
                      cam['name'] ?? 'Camera $idx',
                      style: TextStyle(
                        color: selected ? Colors.white : Colors.white70,
                        fontSize: 13,
                      ),
                    ),
                    selected: selected,
                    onSelected: (_) => _toggleCameraSelection(idx),
                    selectedColor: Colors.blue,
                    checkmarkColor: Colors.white,
                    backgroundColor: Colors.grey[800],
                  );
                }).toList(),
              ),
            ),

          // Active cameras info during streaming
          if (_isStreaming && _selectedCameras.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  const Icon(Icons.videocam, size: 20, color: Colors.green),
                  const SizedBox(width: 8),
                  Text(
                    '${_selectedCameras.length} camera(s) streaming',
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
              onPressed: _cameras.isEmpty
                  ? null
                  : (_isStreaming ? _stopStreaming : _startStreaming),
              icon: Icon(_isStreaming ? Icons.stop : Icons.play_arrow),
              label: Text(
                _isStreaming ? 'Stop Streaming' : 'Start Streaming',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
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
    _loadingTimeoutTimer?.cancel();
    for (final sub in _frameSubs.values) {
      sub.cancel();
    }
    _cameraListSub?.cancel();
    _cameraInfoSub?.cancel();
    _cameraController.dispose();
    super.dispose();
  }
}
