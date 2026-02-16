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

  // Screen dimensions reported by the server (for coordinate mapping)
  int _serverScreenWidth = 1920;
  int _serverScreenHeight = 1080;

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

  // --- Touch-to-mouse input methods ---

  /// Send a tap (left click) at the given screen-relative position.
  /// [relX] and [relY] are 0.0–1.0 fractions of the displayed image.
  void sendTap(double relX, double relY) {
    final x = (relX * _serverScreenWidth).round();
    final y = (relY * _serverScreenHeight).round();
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'input',
      'input_action': 'click',
      'button': 'left',
      'x': x,
      'y': y,
      'count': 1,
    });
  }

  /// Send a double-tap (double click) at the given position.
  void sendDoubleTap(double relX, double relY) {
    final x = (relX * _serverScreenWidth).round();
    final y = (relY * _serverScreenHeight).round();
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'input',
      'input_action': 'click',
      'button': 'left',
      'x': x,
      'y': y,
      'count': 2,
    });
  }

  /// Send a right-click (long press) at the given position.
  void sendRightClick(double relX, double relY) {
    final x = (relX * _serverScreenWidth).round();
    final y = (relY * _serverScreenHeight).round();
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'input',
      'input_action': 'click',
      'button': 'right',
      'x': x,
      'y': y,
      'count': 1,
    });
  }

  /// Send mouse-down (start drag) at the given position.
  void sendMouseDown(double relX, double relY) {
    final x = (relX * _serverScreenWidth).round();
    final y = (relY * _serverScreenHeight).round();
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'input',
      'input_action': 'press',
      'button': 'left',
      'x': x,
      'y': y,
    });
  }

  /// Send mouse-move (during drag) to absolute position.
  void sendMouseMove(double relX, double relY) {
    final x = (relX * _serverScreenWidth).round();
    final y = (relY * _serverScreenHeight).round();
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'input',
      'input_action': 'move',
      'x': x,
      'y': y,
    });
  }

  /// Send mouse-up (end drag) at the given position.
  void sendMouseUp(double relX, double relY) {
    final x = (relX * _serverScreenWidth).round();
    final y = (relY * _serverScreenHeight).round();
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'input',
      'input_action': 'release',
      'button': 'left',
      'x': x,
      'y': y,
    });
  }

  /// Send scroll at the given position.
  void sendScroll(double relX, double relY, double scrollDx, double scrollDy) {
    final x = (relX * _serverScreenWidth).round();
    final y = (relY * _serverScreenHeight).round();
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'input',
      'input_action': 'scroll',
      'x': x,
      'y': y,
      'dx': scrollDx.round(),
      'dy': scrollDy.round(),
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
    final parsed = displays.map((d) => Map<String, dynamic>.from(d)).toList();
    _displaysController.add(parsed);
    
    // Update server screen dimensions from the selected display
    if (parsed.isNotEmpty) {
      _serverScreenWidth = parsed[0]['width'] ?? 1920;
      _serverScreenHeight = parsed[0]['height'] ?? 1080;
    }
  }

  void updateServerScreenSize(int width, int height) {
    _serverScreenWidth = width;
    _serverScreenHeight = height;
  }

  void dispose() {
    stopStreaming();
    _frameController.close();
    _displaysController.close();
  }
}
