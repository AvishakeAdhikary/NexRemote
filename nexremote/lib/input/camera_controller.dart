import '../core/connection_manager.dart';
import 'dart:async';
import 'dart:typed_data';

/// 4-byte binary header for camera frames
const _cameraHeader = [0x43, 0x41, 0x4D, 0x46]; // "CAMF"

class CameraController {
  final ConnectionManager connectionManager;

  final StreamController<Uint8List> _frameController =
      StreamController<Uint8List>.broadcast();
  final StreamController<List<Map<String, dynamic>>> _cameraListController =
      StreamController<List<Map<String, dynamic>>>.broadcast();
  final StreamController<Map<String, dynamic>> _cameraInfoController =
      StreamController<Map<String, dynamic>>.broadcast();

  StreamSubscription? _binarySubscription;
  StreamSubscription? _jsonSubscription;

  /// Receives JPEG frames from the PC camera
  Stream<Uint8List> get frameStream => _frameController.stream;

  /// List of available PC cameras
  Stream<List<Map<String, dynamic>>> get cameraListStream => _cameraListController.stream;

  /// Camera info updates (started, camera_changed)
  Stream<Map<String, dynamic>> get cameraInfoStream => _cameraInfoController.stream;

  bool isStreaming = false;
  Map<String, dynamic>? currentCameraInfo;

  CameraController(this.connectionManager) {
    // Listen for binary frames (CAMF header)
    _binarySubscription = connectionManager.binaryMessageStream.listen((bytes) {
      if (bytes.length > 4 && _matchesHeader(bytes, _cameraHeader)) {
        _frameController.add(bytes.sublist(4));
      }
    });

    // Listen for JSON messages (camera_list, started, camera_changed)
    _jsonSubscription = connectionManager.messageStream.listen((data) {
      if (data['type'] == 'camera') {
        final action = data['action'];
        if (action == 'camera_list') {
          final cameras = List<Map<String, dynamic>>.from(data['cameras'] ?? []);
          _cameraListController.add(cameras);
        } else if (action == 'started' || action == 'camera_changed') {
          currentCameraInfo = Map<String, dynamic>.from(data['camera_info'] ?? {});
          _cameraInfoController.add(currentCameraInfo!);
        }
      }
    });
  }

  bool _matchesHeader(Uint8List bytes, List<int> header) {
    for (int i = 0; i < header.length; i++) {
      if (bytes[i] != header[i]) return false;
    }
    return true;
  }

  /// Request the list of available cameras on the PC
  void requestCameraList() {
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'list_cameras',
    });
  }

  /// Start streaming from a PC camera
  void startStreaming({int cameraIndex = 0}) {
    isStreaming = true;
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'start',
      'camera_index': cameraIndex,
    });
  }

  /// Stop camera streaming
  void stopStreaming() {
    isStreaming = false;
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'stop',
    });
  }

  /// Switch to a different camera
  void setCamera(int cameraIndex) {
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'set_camera',
      'camera_index': cameraIndex,
    });
  }

  void dispose() {
    stopStreaming();
    _binarySubscription?.cancel();
    _jsonSubscription?.cancel();
    _frameController.close();
    _cameraListController.close();
    _cameraInfoController.close();
  }
}
