import '../core/connection_manager.dart';
import 'dart:convert';
import 'dart:typed_data';

class CameraController {
  final ConnectionManager connectionManager;
  bool isStreaming = false;

  CameraController(this.connectionManager);

  void startStreaming() {
    isStreaming = true;
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'start',
    });
  }

  void stopStreaming() {
    isStreaming = false;
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'stop',
    });
  }

  void sendFrame(Uint8List imageBytes) {
    if (!isStreaming) return;

    // Convert to base64
    final base64Image = base64Encode(imageBytes);

    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'frame',
      'data': base64Image,
    });
  }

  void requestCameraList() {
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'list_cameras',
    });
  }

  void dispose() {
    stopStreaming();
  }
}
