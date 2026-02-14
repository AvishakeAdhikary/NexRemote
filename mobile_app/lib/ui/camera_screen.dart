import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/camera_controller.dart' as cam_ctrl;

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
  late cam_ctrl.CameraController _cameraController;
  CameraController? _camera;
  List<CameraDescription> _cameras = [];
  int _selectedCameraIndex = 0;
  bool _isStreaming = false;
  bool _isInitializing = false;
  Timer? _frameTimer;
  String _resolution = 'Medium';
  int _frameRate = 15;

  @override
  void initState() {
    super.initState();
    _cameraController = cam_ctrl.CameraController(widget.connectionManager);
    _initializeCameras();
  }

  Future<void> _initializeCameras() async {
    try {
      _cameras = await availableCameras();
      if (_cameras.isNotEmpty) {
        await _initializeCamera(_selectedCameraIndex);
      }
    } catch (e) {
      _showError('Failed to initialize cameras: $e');
    }
  }

  Future<void> _initializeCamera(int cameraIndex) async {
    if (_isInitializing) return;

    setState(() {
      _isInitializing = true;
    });

    try {
      // Dispose previous camera
      await _camera?.dispose();

      // Initialize new camera
      _camera = CameraController(
        _cameras[cameraIndex],
        _getResolutionPreset(),
        enableAudio: false,
      );

      await _camera!.initialize();

      if (mounted) {
        setState(() {
          _selectedCameraIndex = cameraIndex;
          _isInitializing = false;
        });
      }
    } catch (e) {
      _showError('Failed to initialize camera: $e');
      setState(() {
        _isInitializing = false;
      });
    }
  }

  ResolutionPreset _getResolutionPreset() {
    switch (_resolution) {
      case 'Low':
        return ResolutionPreset.low;
      case 'Medium':
        return ResolutionPreset.medium;
      case 'High':
        return ResolutionPreset.high;
      default:
        return ResolutionPreset.medium;
    }
  }

  void _toggleStreaming() {
    if (_isStreaming) {
      _stopStreaming();
    } else {
      _startStreaming();
    }
  }

  void _startStreaming() {
    if (_camera == null || !_camera!.value.isInitialized) {
      _showError('Camera not initialized');
      return;
    }

    setState(() {
      _isStreaming = true;
    });

    _cameraController.startStreaming();

    // Start sending frames at specified frame rate
    final interval = Duration(milliseconds: (1000 / _frameRate).round());
    _frameTimer = Timer.periodic(interval, (timer) async {
      if (_camera != null && _camera!.value.isInitialized && _isStreaming) {
        try {
          final image = await _camera!.takePicture();
          final bytes = await image.readAsBytes();
          _cameraController.sendFrame(bytes);
        } catch (e) {
          // Ignore frame capture errors
        }
      }
    });
  }

  void _stopStreaming() {
    _frameTimer?.cancel();
    _frameTimer = null;

    setState(() {
      _isStreaming = false;
    });

    _cameraController.stopStreaming();
  }

  void _switchCamera(int index) async {
    if (index == _selectedCameraIndex) return;

    final wasStreaming = _isStreaming;
    if (wasStreaming) {
      _stopStreaming();
    }

    await _initializeCamera(index);

    if (wasStreaming) {
      _startStreaming();
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
                      Icon(
                        _cameras[index].lensDirection == CameraLensDirection.front
                            ? Icons.camera_front
                            : Icons.camera_rear,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _cameras[index].lensDirection == CameraLensDirection.front
                            ? 'Front Camera'
                            : 'Rear Camera',
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
    if (_isInitializing) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_camera == null || !_camera!.value.isInitialized) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.camera_alt,
              size: 100,
              color: Colors.grey[600],
            ),
            const SizedBox(height: 24),
            Text(
              'Camera not available',
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey[400],
              ),
            ),
          ],
        ),
      );
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        Container(
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
            child: CameraPreview(_camera!),
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
                color: Colors.red,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: const [
                  Icon(Icons.fiber_manual_record, size: 12, color: Colors.white),
                  SizedBox(width: 6),
                  Text(
                    'STREAMING',
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

        // Frame rate indicator
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
              child: Text(
                '$_frameRate FPS',
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
          // Resolution selector
          Row(
            children: [
              const Icon(Icons.high_quality, size: 20, color: Colors.blue),
              const SizedBox(width: 12),
              const Text('Resolution:'),
              const SizedBox(width: 12),
              Expanded(
                child: SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'Low', label: Text('Low')),
                    ButtonSegment(value: 'Medium', label: Text('Med')),
                    ButtonSegment(value: 'High', label: Text('High')),
                  ],
                  selected: {_resolution},
                  onSelectionChanged: (Set<String> selected) async {
                    if (!_isStreaming) {
                      setState(() {
                        _resolution = selected.first;
                      });
                      await _initializeCamera(_selectedCameraIndex);
                    }
                  },
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Frame rate selector
          Row(
            children: [
              const Icon(Icons.speed, size: 20, color: Colors.blue),
              const SizedBox(width: 12),
              const Text('FPS:'),
              Expanded(
                child: Slider(
                  value: _frameRate.toDouble(),
                  min: 5,
                  max: 30,
                  divisions: 5,
                  label: '$_frameRate',
                  onChanged: _isStreaming
                      ? null
                      : (value) {
                          setState(() {
                            _frameRate = value.round();
                          });
                        },
                ),
              ),
              Text('$_frameRate'),
              const SizedBox(width: 8),
            ],
          ),

          const SizedBox(height: 12),

          // Start/Stop button
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              onPressed: _camera?.value.isInitialized == true ? _toggleStreaming : null,
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
    _stopStreaming();
    _camera?.dispose();
    _cameraController.dispose();
    super.dispose();
  }
}
