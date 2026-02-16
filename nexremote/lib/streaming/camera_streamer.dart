import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import '../core/connection_manager.dart';
import '../utils/logger.dart';

class CameraStreamer {
  final ConnectionManager connectionManager;
  
  CameraController? _cameraController;
  bool _isStreaming = false;
  
  CameraStreamer(this.connectionManager);
  
  Future<List<CameraDescription>> getAvailableCameras() async {
    return await availableCameras();
  }
  
  Future<bool> startStreaming({int cameraIndex = 0}) async {
    try {
      final cameras = await getAvailableCameras();
      if (cameras.isEmpty) {
        Logger.error('No cameras available');
        return false;
      }
      
      _cameraController = CameraController(
        cameras[cameraIndex],
        ResolutionPreset.medium,
        enableAudio: false,
      );
      
      await _cameraController!.initialize();
      
      _isStreaming = true;
      _startFrameCapture();
      
      Logger.info('Camera streaming started');
      return true;
    } catch (e) {
      Logger.error('Failed to start camera streaming: $e');
      return false;
    }
  }
  
  void _startFrameCapture() async {
    while (_isStreaming && _cameraController != null) {
      try {
        final image = await _cameraController!.takePicture();
        final bytes = await image.readAsBytes();
        final base64Image = base64Encode(bytes);
        
        connectionManager.sendMessage({
          'type': 'camera_frame',
          'data': base64Image,
        });
        
        // Delay to control frame rate (~10 FPS)
        await Future.delayed(const Duration(milliseconds: 100));
      } catch (e) {
        Logger.error('Error capturing frame: $e');
      }
    }
  }
  
  void stopStreaming() {
    _isStreaming = false;
    _cameraController?.dispose();
    _cameraController = null;
    Logger.info('Camera streaming stopped');
  }
  
  bool get isStreaming => _isStreaming;
  
  void dispose() {
    stopStreaming();
  }
}