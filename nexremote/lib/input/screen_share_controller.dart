import '../core/connection_manager.dart';
import 'dart:async';
import 'dart:typed_data';

/// Binary frame header: "SCRN" (4 bytes) + monitor_index 0-based (1 byte) = 5 bytes total.
const _headerMagic = [0x53, 0x43, 0x52, 0x4E]; // "SCRN"
const _headerLen = 5;

bool _matchesScreenHeader(Uint8List bytes) {
  if (bytes.length < _headerLen) return false;
  for (int i = 0; i < 4; i++) {
    if (bytes[i] != _headerMagic[i]) return false;
  }
  return true;
}

/// Immutable description of one physical display as reported by the server.
class DisplayInfo {
  final int index;        // 0-based client index
  final String name;
  final int width;
  final int height;
  final bool isPrimary;

  const DisplayInfo({
    required this.index,
    required this.name,
    required this.width,
    required this.height,
    this.isPrimary = false,
  });

  factory DisplayInfo.fromJson(Map<String, dynamic> json) => DisplayInfo(
    index:     (json['index'] as num).toInt(),
    name:      json['name'] as String? ?? 'Display',
    width:     (json['width'] as num?)?.toInt() ?? 1920,
    height:    (json['height'] as num?)?.toInt() ?? 1080,
    isPrimary: json['is_primary'] as bool? ?? false,
  );

  String get resolution => '${width}x$height';
}

/// Per-monitor frame stream: emits JPEG [Uint8List] whenever a new frame arrives
/// for that monitor index.
class MonitorFrameStream {
  final int monitorIndex;
  final _ctrl = StreamController<Uint8List>.broadcast();

  MonitorFrameStream(this.monitorIndex);

  Stream<Uint8List> get stream => _ctrl.stream;

  void add(Uint8List frame) {
    if (!_ctrl.isClosed) _ctrl.add(frame);
  }

  void close() => _ctrl.close();
}

/// Handles all screen share commands and exposes per-monitor frame streams.
class ScreenShareController {
  final ConnectionManager connectionManager;

  // Per-monitor frame streams, keyed by 0-based monitor index
  final _monitorStreams = <int, MonitorFrameStream>{};

  final _displaysCtrl =
      StreamController<List<DisplayInfo>>.broadcast();
  Stream<List<DisplayInfo>> get displaysStream => _displaysCtrl.stream;

  // Legacy single-stream API — emits frames from the first active monitor
  final _legacyCtrl = StreamController<Uint8List>.broadcast();
  Stream<Uint8List> get frameStream => _legacyCtrl.stream;

  bool isStreaming = false;
  List<int> activeMonitorIndices = [];

  // Server screen dimensions per monitor (for coordinate mapping)
  final _screenSizes = <int, (int, int)>{};  // monitorIndex → (w, h)
  int _primaryMonitorIndex = 0;

  int get serverScreenWidth =>
      _screenSizes[_primaryMonitorIndex]?.$1 ?? 1920;
  int get serverScreenHeight =>
      _screenSizes[_primaryMonitorIndex]?.$2 ?? 1080;

  int currentFps = 30;
  String currentResolution = 'native';
  int currentQuality = 70;

  StreamSubscription? _binarySub;
  StreamSubscription? _jsonSub;

  ScreenShareController(this.connectionManager) {
    _binarySub = connectionManager.binaryMessageStream.listen(_onBinary);
    _jsonSub =
        connectionManager.messageStream.listen(_onJson);
  }

  // ── Binary frame routing ─────────────────────────────────────────────────

  void _onBinary(Uint8List bytes) {
    if (!_matchesScreenHeader(bytes)) return;
    final monIdx = bytes[4];              // 0-based monitor index
    final jpeg = bytes.sublist(_headerLen);

    // Route to per-monitor stream
    _monitorStreams.putIfAbsent(monIdx, () => MonitorFrameStream(monIdx)).add(jpeg);

    // Also emit on legacy single-stream (for backwards compat)
    if (!_legacyCtrl.isClosed) _legacyCtrl.add(jpeg);
  }

  // ── JSON message handling ────────────────────────────────────────────────

  void _onJson(Map<String, dynamic> data) {
    if (data['type'] != 'screen_share') return;
    final action = data['action'];

    if (action == 'display_list') {
      final raw = data['displays'] as List? ?? [];
      final displays =
          raw.map((d) => DisplayInfo.fromJson(d as Map<String, dynamic>)).toList();

      // Index screen sizes for coordinate mapping
      for (final d in displays) {
        _screenSizes[d.index] = (d.width, d.height);
        if (d.isPrimary) _primaryMonitorIndex = d.index;
      }

      // Active displays reported by server
      final activeRaw = data['active_displays'] as List? ?? [];
      activeMonitorIndices = activeRaw.map((e) => (e as num).toInt()).toList();

      if (!_displaysCtrl.isClosed) _displaysCtrl.add(displays);

      if (data['current_fps'] != null) currentFps = data['current_fps'];
      if (data['current_quality'] != null) currentQuality = data['current_quality'];
      if (data['current_resolution'] != null) {
        currentResolution = data['current_resolution'];
      }
    }
  }

  // ── Per-monitor streams ──────────────────────────────────────────────────

  /// Returns a broadcast stream of JPEG frames for [monitorIndex].
  Stream<Uint8List> frameStreamForMonitor(int monitorIndex) {
    return _monitorStreams
        .putIfAbsent(monitorIndex, () => MonitorFrameStream(monitorIndex))
        .stream;
  }

  // ── Commands ─────────────────────────────────────────────────────────────

  /// Start streaming one or more monitors simultaneously.
  void startStreaming({
    List<int> displayIndices = const [0],
    int fps = 30,
    String quality = 'medium',
    String resolution = 'native',
  }) {
    isStreaming = true;
    activeMonitorIndices = List.of(displayIndices);

    int qv;
    switch (quality) {
      case 'low':   qv = 30; break;
      case 'medium': qv = 50; break;
      case 'high':   qv = 70; break;
      case 'ultra':  qv = 90; break;
      default:       qv = 50;
    }
    currentFps = fps;
    currentQuality = qv;
    currentResolution = resolution;

    connectionManager.sendMessage({
      'type': 'screen_share',
      'action': 'start',
      'display_index':   displayIndices.first,   // legacy compat
      'display_indices': displayIndices,          // multi-monitor
      'fps':        fps,
      'quality':    qv,
      'resolution': resolution,
    });
  }

  void stopStreaming({int? displayIndex}) {
    if (displayIndex == null) {
      isStreaming = false;
      activeMonitorIndices = [];
    } else {
      activeMonitorIndices.remove(displayIndex);
      if (activeMonitorIndices.isEmpty) isStreaming = false;
    }
    final msg = <String, dynamic>{
      'type': 'screen_share',
      'action': 'stop',
    };
    if (displayIndex != null) msg['display_index'] = displayIndex;
    connectionManager.sendMessage(msg);
  }

  void setFps(int fps) {
    currentFps = fps;
    connectionManager.sendMessage({'type': 'screen_share', 'action': 'set_fps', 'fps': fps});
  }

  void setQuality(int quality) {
    currentQuality = quality;
    connectionManager.sendMessage({'type': 'screen_share', 'action': 'set_quality', 'quality': quality});
  }

  void setResolution(String resolution) {
    currentResolution = resolution;
    connectionManager.sendMessage({'type': 'screen_share', 'action': 'set_resolution', 'resolution': resolution});
  }

  void requestDisplayList() {
    connectionManager.sendMessage({'type': 'screen_share', 'action': 'list_displays'});
  }

  // ── Interactive input ────────────────────────────────────────────────────

  void _sendInput(Map<String, dynamic> extra) {
    connectionManager.sendMessage({'type': 'screen_share', 'action': 'input', ...extra});
  }

  void sendTap(double rx, double ry, {int monitorIndex = 0}) {
    final (w, h) = _screenSizes[monitorIndex] ?? (1920, 1080);
    _sendInput({'input_action': 'click', 'button': 'left',
      'x': (rx * w).round(), 'y': (ry * h).round(), 'count': 1});
  }

  void sendDoubleTap(double rx, double ry, {int monitorIndex = 0}) {
    final (w, h) = _screenSizes[monitorIndex] ?? (1920, 1080);
    _sendInput({'input_action': 'click', 'button': 'left',
      'x': (rx * w).round(), 'y': (ry * h).round(), 'count': 2});
  }

  void sendRightClick(double rx, double ry, {int monitorIndex = 0}) {
    final (w, h) = _screenSizes[monitorIndex] ?? (1920, 1080);
    _sendInput({'input_action': 'click', 'button': 'right',
      'x': (rx * w).round(), 'y': (ry * h).round(), 'count': 1});
  }

  void sendMouseDown(double rx, double ry, {int monitorIndex = 0}) {
    final (w, h) = _screenSizes[monitorIndex] ?? (1920, 1080);
    _sendInput({'input_action': 'press', 'button': 'left',
      'x': (rx * w).round(), 'y': (ry * h).round()});
  }

  void sendMouseMove(double rx, double ry, {int monitorIndex = 0}) {
    final (w, h) = _screenSizes[monitorIndex] ?? (1920, 1080);
    _sendInput({'input_action': 'move',
      'x': (rx * w).round(), 'y': (ry * h).round()});
  }

  void sendMouseUp(double rx, double ry, {int monitorIndex = 0}) {
    final (w, h) = _screenSizes[monitorIndex] ?? (1920, 1080);
    _sendInput({'input_action': 'release', 'button': 'left',
      'x': (rx * w).round(), 'y': (ry * h).round()});
  }

  void sendScroll(double rx, double ry, double dx, double dy, {int monitorIndex = 0}) {
    final (w, h) = _screenSizes[monitorIndex] ?? (1920, 1080);
    _sendInput({'input_action': 'scroll',
      'x': (rx * w).round(), 'y': (ry * h).round(),
      'dx': dx.round(), 'dy': dy.round()});
  }

  void updateServerScreenSize(int width, int height) {
    _screenSizes[_primaryMonitorIndex] = (width, height);
  }

  void dispose() {
    stopStreaming();
    _binarySub?.cancel();
    _jsonSub?.cancel();
    for (final s in _monitorStreams.values) { s.close(); }
    _monitorStreams.clear();
    _legacyCtrl.close();
    _displaysCtrl.close();
  }
}
