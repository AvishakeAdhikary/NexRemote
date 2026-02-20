import 'dart:async';
import '../core/connection_manager.dart';

/// Immutable snapshot of the current Windows media state pushed from the server.
class MediaState {
  final int volume;        // 0–100, or -1 if unknown
  final bool isMuted;
  final bool isPlaying;
  final bool hasMedia;
  final String title;
  final String artist;

  const MediaState({
    this.volume = 50,
    this.isMuted = false,
    this.isPlaying = false,
    this.hasMedia = false,
    this.title = 'No Media Playing',
    this.artist = '',
  });

  MediaState copyWith({
    int? volume,
    bool? isMuted,
    bool? isPlaying,
    bool? hasMedia,
    String? title,
    String? artist,
  }) => MediaState(
    volume: volume ?? this.volume,
    isMuted: isMuted ?? this.isMuted,
    isPlaying: isPlaying ?? this.isPlaying,
    hasMedia: hasMedia ?? this.hasMedia,
    title: title ?? this.title,
    artist: artist ?? this.artist,
  );

  factory MediaState.fromJson(Map<String, dynamic> json) => MediaState(
    volume: (json['volume'] as num?)?.toInt() ?? -1,
    isMuted: json['is_muted'] as bool? ?? false,
    isPlaying: json['is_playing'] as bool? ?? false,
    hasMedia: json['has_media'] as bool? ?? false,
    title: json['title'] as String? ?? 'No Media Playing',
    artist: json['artist'] as String? ?? '',
  );
}

/// Handles all media control commands and exposes a [stateStream] that emits
/// the authoritative Windows media state pushed by the server every ~1.5 s.
class MediaController {
  final ConnectionManager connectionManager;

  final _stateController = StreamController<MediaState>.broadcast();

  /// Emits a new [MediaState] every time the server pushes an update.
  Stream<MediaState> get stateStream => _stateController.stream;

  StreamSubscription? _msgSub;

  MediaController(this.connectionManager) {
    // Subscribe to server-pushed media_info messages
    _msgSub = connectionManager.messageStream.listen((msg) {
      if (msg['type'] == 'media_control' && msg['action'] == 'media_info') {
        if (!_stateController.isClosed) {
          _stateController.add(MediaState.fromJson(msg));
        }
      }
    });
  }

  // ── Commands ───────────────────────────────────────────────────────────────

  void play() => _send({'type': 'media_control', 'action': 'play'});
  void pause() => _send({'type': 'media_control', 'action': 'pause'});
  void stop() => _send({'type': 'media_control', 'action': 'stop'});
  void next() => _send({'type': 'media_control', 'action': 'next'});
  void previous() => _send({'type': 'media_control', 'action': 'previous'});
  void toggleMute() => _send({'type': 'media_control', 'action': 'mute_toggle'});
  void volumeUp() => _send({'type': 'media_control', 'action': 'volume_up'});
  void volumeDown() => _send({'type': 'media_control', 'action': 'volume_down'});

  void setVolume(int volume) => _send({
    'type': 'media_control',
    'action': 'volume',
    'value': volume,
  });

  /// Request an immediate media state update from the server.
  /// The server's push loop will also send one automatically every 1.5 s,
  /// but calling this gives an instant response when first opening the screen.
  void requestMediaInfo() => _send({
    'type': 'media_control',
    'action': 'get_info',
  });

  void seek(double position) => _send({
    'type': 'media_control',
    'action': 'seek',
    'position': position,
  });

  void _send(Map<String, dynamic> msg) =>
      connectionManager.sendMessage(msg);

  void dispose() {
    _msgSub?.cancel();
    _stateController.close();
  }
}
