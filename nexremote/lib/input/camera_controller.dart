import '../core/connection_manager.dart';
import 'dart:async';
import 'dart:typed_data';

/// 4-byte binary header for camera frames
const _cameraHeader = [0x43, 0x41, 0x4D, 0x46]; // "CAMF"

class CameraController {
  final ConnectionManager connectionManager;

  /// Per-camera frame streams (keyed by camera_index)
  final Map<int, StreamController<Uint8List>> _frameControllers = {};

  /// Legacy single-stream (camera 0 or first active camera)
  final StreamController<Uint8List> _defaultFrameController =
      StreamController<Uint8List>.broadcast();

  final StreamController<List<Map<String, dynamic>>> _cameraListController =
      StreamController<List<Map<String, dynamic>>>.broadcast();
  final StreamController<Map<String, dynamic>> _cameraInfoController =
      StreamController<Map<String, dynamic>>.broadcast();

  StreamSubscription? _binarySubscription;
  StreamSubscription? _jsonSubscription;

  /// Default frame stream (backward-compatible, streams camera 0)
  Stream<Uint8List> get frameStream => _defaultFrameController.stream;

  /// Get frame stream for a specific camera
  Stream<Uint8List> frameStreamFor(int cameraIndex) {
    _frameControllers.putIfAbsent(
      cameraIndex,
      () => StreamController<Uint8List>.broadcast(),
    );
    return _frameControllers[cameraIndex]!.stream;
  }

  Stream<List<Map<String, dynamic>>> get cameraListStream =>
      _cameraListController.stream;
  Stream<Map<String, dynamic>> get cameraInfoStream =>
      _cameraInfoController.stream;

  bool isStreaming = false;
  Set<int> activeStreams = {};
  Map<String, dynamic>? currentCameraInfo;

  CameraController(this.connectionManager) {
    // Listen for binary frames: CAMF (4 bytes) + camera_index (1 byte) + JPEG
    _binarySubscription = connectionManager.binaryMessageStream.listen((bytes) {
      if (bytes.length > 5 && _matchesHeader(bytes, _cameraHeader)) {
        final camIdx = bytes[4]; // 5th byte = camera index
        final jpeg = bytes.sublist(5);

        // Per-camera stream
        _frameControllers.putIfAbsent(
          camIdx,
          () => StreamController<Uint8List>.broadcast(),
        );
        _frameControllers[camIdx]!.add(jpeg);

        // Default stream (always camera 0, or first if no 0)
        if (camIdx == 0 || activeStreams.isEmpty) {
          _defaultFrameController.add(jpeg);
        }
      } else if (bytes.length > 4 && _matchesHeader(bytes, _cameraHeader)) {
        // Backward compatibility: old 4-byte header without camera index
        _defaultFrameController.add(bytes.sublist(4));
        _frameControllers.putIfAbsent(
          0,
          () => StreamController<Uint8List>.broadcast(),
        );
        _frameControllers[0]!.add(bytes.sublist(4));
      }
    });

    // Listen for JSON messages
    _jsonSubscription = connectionManager.messageStream.listen((data) {
      if (data['type'] == 'camera') {
        final action = data['action'];
        if (action == 'camera_list') {
          final cameras = List<Map<String, dynamic>>.from(
            data['cameras'] ?? [],
          );
          _cameraListController.add(cameras);
        } else if (action == 'started' || action == 'camera_changed') {
          currentCameraInfo = Map<String, dynamic>.from(
            data['camera_info'] ?? {},
          );
          _cameraInfoController.add(currentCameraInfo!);
        } else if (action == 'multi_started') {
          final indices = List<int>.from(data['camera_indices'] ?? []);
          activeStreams = indices.toSet();
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

  void requestCameraList() {
    connectionManager.sendMessage({'type': 'camera', 'action': 'list_cameras'});
  }

  /// Start streaming from a single PC camera
  void startStreaming({int cameraIndex = 0}) {
    isStreaming = true;
    activeStreams.add(cameraIndex);
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'start',
      'camera_index': cameraIndex,
    });
  }

  /// Start streaming from multiple cameras simultaneously
  void startMultiStreaming(List<int> cameraIndices) {
    isStreaming = true;
    activeStreams = cameraIndices.toSet();
    connectionManager.sendMessage({
      'type': 'camera',
      'action': 'start_multi',
      'camera_indices': cameraIndices,
    });
  }

  /// Stop a specific camera stream
  void stopStreaming({int? cameraIndex}) {
    if (cameraIndex != null) {
      activeStreams.remove(cameraIndex);
      connectionManager.sendMessage({
        'type': 'camera',
        'action': 'stop',
        'camera_index': cameraIndex,
      });
    } else {
      // Stop all
      isStreaming = false;
      activeStreams.clear();
      connectionManager.sendMessage({'type': 'camera', 'action': 'stop_all'});
    }

    if (activeStreams.isEmpty) {
      isStreaming = false;
    }
  }

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
    _defaultFrameController.close();
    for (final ctrl in _frameControllers.values) {
      ctrl.close();
    }
    _cameraListController.close();
    _cameraInfoController.close();
  }
}
