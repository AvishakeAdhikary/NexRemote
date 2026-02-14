import '../core/connection_manager.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';

class ScreenShareController {
  final ConnectionManager connectionManager;
  final StreamController<Uint8List> _frameController =
      StreamController<Uint8List>.broadcast();
  final StreamController<List<Map<String, dynamic>>> _displaysController =
      StreamController<List<Map<String, dynamic>>>.broadcast();

  Stream<Uint8List> get frameStream => _frameController.stream;
  Stream<List<Map<String, dynamic>>> get displaysStream => _displaysController.stream;

  bool isStreaming = false;
  Timer? _refreshTimer;

  ScreenShareController(this.connectionManager);

  void startStreaming({int displayIndex = 0, int fps = 10, String quality = 'medium'}) {
    isStreaming = true;

    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'start',
      'display_index': displayIndex,
      'quality': quality,
    });

    // Request frames at specified FPS
    final interval = Duration(milliseconds: (1000 / fps).round());
    _refreshTimer = Timer.periodic(interval, (timer) {
      if (isStreaming) {
        requestFrame(displayIndex);
      }
    });
  }

  void stopStreaming() {
    isStreaming = false;
    _refreshTimer?.cancel();
    _refreshTimer = null;

    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'stop',
    });
  }

  void requestFrame(int displayIndex) {
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'request_frame',
      'display_index': displayIndex,
    });
  }

  void requestDisplayList() {
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'list_displays',
    });
  }

  void handleFrame(String base64Data) {
    try {
      final bytes = base64Decode(base64Data);
      _frameController.add(bytes);
    } catch (e) {
      if (kDebugMode) {
        print('Error decoding frame: $e');
      }
    }
  }

  void handleDisplayList(List<dynamic> displays) {
    _displaysController.add(
      displays.map((d) => Map<String, dynamic>.from(d)).toList(),
    );
  }

  void dispose() {
    stopStreaming();
    _frameController.close();
    _displaysController.close();
  }
}
