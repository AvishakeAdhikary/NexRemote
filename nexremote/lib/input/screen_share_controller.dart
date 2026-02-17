import '../core/connection_manager.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';

/// 4-byte binary header for screen frames
const _screenHeader = [0x53, 0x43, 0x52, 0x4E]; // "SCRN"

class ScreenShareController {
  final ConnectionManager connectionManager;
  final StreamController<Uint8List> _frameController =
      StreamController<Uint8List>.broadcast();
  final StreamController<List<Map<String, dynamic>>> _displaysController =
      StreamController<List<Map<String, dynamic>>>.broadcast();

  StreamSubscription? _binarySubscription;
  StreamSubscription? _jsonSubscription;

  Stream<Uint8List> get frameStream => _frameController.stream;
  Stream<List<Map<String, dynamic>>> get displaysStream => _displaysController.stream;

  bool isStreaming = false;

  // Screen dimensions reported by the server (for coordinate mapping)
  int _serverScreenWidth = 1920;
  int _serverScreenHeight = 1080;

  // Current settings
  int currentFps = 30;
  String currentResolution = 'native';
  int currentQuality = 70;

  ScreenShareController(this.connectionManager) {
    // Listen for binary frames (SCRN header)
    _binarySubscription = connectionManager.binaryMessageStream.listen((bytes) {
      if (bytes.length > 4 && _matchesHeader(bytes, _screenHeader)) {
        // Strip the 4-byte header, pass JPEG bytes
        _frameController.add(bytes.sublist(4));
      }
    });

    // Listen for JSON messages (display_list, etc.)
    _jsonSubscription = connectionManager.messageStream.listen((data) {
      if (data['type'] == 'screen_share') {
        final action = data['action'];
        if (action == 'display_list') {
          final displays = List<Map<String, dynamic>>.from(data['displays'] ?? []);
          _displaysController.add(displays);

          // Update settings from server
          if (data['current_fps'] != null) currentFps = data['current_fps'];
          if (data['current_quality'] != null) currentQuality = data['current_quality'];
          if (data['current_resolution'] != null) currentResolution = data['current_resolution'];

          // Update server screen dimensions from the selected display
          if (displays.isNotEmpty) {
            _serverScreenWidth = displays[0]['width'] ?? 1920;
            _serverScreenHeight = displays[0]['height'] ?? 1080;
          }
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

  void startStreaming({
    int displayIndex = 0,
    int fps = 30,
    String quality = 'medium',
    String resolution = 'native',
  }) {
    isStreaming = true;

    // Map quality name to value
    int qualityValue;
    switch (quality) {
      case 'low':
        qualityValue = 30;
        break;
      case 'medium':
        qualityValue = 50;
        break;
      case 'high':
        qualityValue = 70;
        break;
      case 'ultra':
        qualityValue = 90;
        break;
      default:
        qualityValue = 50;
    }

    currentFps = fps;
    currentQuality = qualityValue;
    currentResolution = resolution;

    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'start',
      'display_index': displayIndex,
      'fps': fps,
      'quality': qualityValue,
      'resolution': resolution,
    });
  }

  void stopStreaming() {
    isStreaming = false;

    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'stop',
    });
  }

  void setFps(int fps) {
    currentFps = fps;
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'set_fps',
      'fps': fps,
    });
  }

  void setQuality(int quality) {
    currentQuality = quality;
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'set_quality',
      'quality': quality,
    });
  }

  void setResolution(String resolution) {
    currentResolution = resolution;
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'set_resolution',
      'resolution': resolution,
    });
  }

  void setMonitor(int monitorIndex) {
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'set_monitor',
      'monitor_index': monitorIndex,
    });
  }

  void requestDisplayList() {
    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'list_displays',
    });
  }

  // --- Touch-to-mouse input methods ---

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

  void updateServerScreenSize(int width, int height) {
    _serverScreenWidth = width;
    _serverScreenHeight = height;
  }

  void dispose() {
    stopStreaming();
    _binarySubscription?.cancel();
    _jsonSubscription?.cancel();
    _frameController.close();
    _displaysController.close();
  }
}
