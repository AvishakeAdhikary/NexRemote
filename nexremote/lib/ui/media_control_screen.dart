import 'package:flutter/material.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/media_controller.dart';

class MediaControlScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const MediaControlScreen({
    super.key,
    required this.connectionManager,
  });

  @override
  State<MediaControlScreen> createState() => _MediaControlScreenState();
}

class _MediaControlScreenState extends State<MediaControlScreen> {
  late MediaController _controller;
  StreamSubscription<MediaState>? _stateSub;

  // Authoritative state — always from server
  MediaState _state = const MediaState();

  // Volume drag: show local value while thumb is held down
  double? _pendingVolume;

  // Command cooldown: after any user command, suppress server pushes for
  // 2 seconds so optimistic UI isn't clobbered before Windows catches up.
  static const _cooldownMs = 2000;
  DateTime? _lastCommandAt;

  bool get _inCooldown =>
      _lastCommandAt != null &&
      DateTime.now().difference(_lastCommandAt!).inMilliseconds < _cooldownMs;

  void _markCommand() => _lastCommandAt = DateTime.now();

  @override
  void initState() {
    super.initState();
    _controller = MediaController(widget.connectionManager);

    _stateSub = _controller.stateStream.listen((state) {
      if (!mounted) return;
      // Ignore server pushes during cooldown — prevents icon glitch where
      // Windows hasn't processed the key-press yet and pushes stale state.
      if (_inCooldown) return;
      setState(() => _state = state);
    });

    // Request immediate state so the screen isn't blank for the first 1.5 s
    _controller.requestMediaInfo();
  }

  @override
  void dispose() {
    _stateSub?.cancel();
    _controller.dispose();
    super.dispose();
  }

  // ── Commands ──────────────────────────────────────────────────────────────

  void _togglePlayPause() {
    _markCommand();
    if (_state.isPlaying) {
      _controller.pause();
      setState(() => _state = _state.copyWith(isPlaying: false));
    } else {
      _controller.play();
      setState(() => _state = _state.copyWith(isPlaying: true));
    }
  }

  void _stop() {
    _markCommand();
    _controller.stop();
    setState(() => _state = _state.copyWith(isPlaying: false));
  }

  void _next() {
    _markCommand();
    _controller.next();
  }

  void _previous() {
    _markCommand();
    _controller.previous();
  }

  void _toggleMute() {
    _markCommand();
    _controller.toggleMute();
    setState(() => _state = _state.copyWith(isMuted: !_state.isMuted));
  }

  void _onVolumeChanged(double value) {
    setState(() => _pendingVolume = value);
  }

  void _onVolumeChangeEnd(double value) {
    final v = value.round();
    _markCommand();
    _controller.setVolume(v);
    setState(() {
      _state = _state.copyWith(volume: v);
      _pendingVolume = null;
    });
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final isLandscape =
        MediaQuery.of(context).orientation == Orientation.landscape;

    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0F),
      appBar: AppBar(
        title: const Text('Media Control'),
        backgroundColor: const Color(0xFF0D0D0F),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SafeArea(
        child: isLandscape ? _buildLandscape() : _buildPortrait(),
      ),
    );
  }

  Widget _buildPortrait() => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            _buildAlbumArt(),
            const SizedBox(height: 28),
            _buildNowPlaying(),
            const SizedBox(height: 36),
            _buildPlaybackControls(),
            const SizedBox(height: 32),
            _buildVolumeControl(),
          ],
        ),
      );

  Widget _buildLandscape() => Row(
        children: [
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildAlbumArt(),
                const SizedBox(height: 16),
                _buildNowPlaying(),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _buildPlaybackControls(),
                  const SizedBox(height: 24),
                  _buildVolumeControl(),
                ],
              ),
            ),
          ),
        ],
      );

  // ── Widgets ────────────────────────────────────────────────────────────────

  Widget _buildAlbumArt() {
    final active = _state.hasMedia;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 400),
      width: 200,
      height: 200,
      decoration: BoxDecoration(
        color: active ? const Color(0xFF1A1F3A) : const Color(0xFF1A1A1A),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: active ? Colors.blueAccent : Colors.grey[700]!,
          width: 2,
        ),
        boxShadow: active
            ? [
                BoxShadow(
                  color: Colors.blueAccent.withAlpha(80),
                  blurRadius: 30,
                  spreadRadius: 6,
                )
              ]
            : [],
      ),
      child: Icon(
        active
            ? (_state.isPlaying ? Icons.music_note : Icons.pause_circle_outline)
            : Icons.music_off,
        size: 90,
        color: active ? Colors.blueAccent : Colors.grey[600],
      ),
    );
  }

  Widget _buildNowPlaying() => Column(
        children: [
          Text(
            _state.title,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          if (_state.artist.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              _state.artist,
              style: TextStyle(fontSize: 15, color: Colors.grey[400]),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      );

  Widget _buildPlaybackControls() => Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _circleBtn(Icons.skip_previous_rounded, _previous, 56),
          const SizedBox(width: 16),
          _circleBtn(Icons.stop_rounded, _stop, 52, accent: Colors.redAccent),
          const SizedBox(width: 16),
          _circleBtn(
            _state.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
            _togglePlayPause,
            76,
            primary: true,
          ),
          const SizedBox(width: 16),
          _circleBtn(Icons.skip_next_rounded, _next, 56),
        ],
      );

  Widget _circleBtn(
    IconData icon,
    VoidCallback onTap,
    double size, {
    bool primary = false,
    Color? accent,
  }) {
    final bg = primary
        ? Colors.blueAccent
        : accent != null
            ? accent.withAlpha(35)
            : const Color(0xFF1A1A2E);
    final border = primary ? Colors.blue[300]! : (accent ?? Colors.blueAccent);

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: bg,
          shape: BoxShape.circle,
          border: Border.all(color: border, width: 2),
          boxShadow: primary
              ? [
                  BoxShadow(
                    color: Colors.blueAccent.withAlpha(100),
                    blurRadius: 20,
                    spreadRadius: 3,
                  )
                ]
              : null,
        ),
        child: Icon(icon, size: size * 0.45, color: Colors.white),
      ),
    );
  }

  Widget _buildVolumeControl() {
    final displayVol = _pendingVolume?.round() ??
        (_state.volume >= 0 ? _state.volume : 50);
    final sliderVal = (_pendingVolume ?? displayVol.toDouble()).clamp(0.0, 100.0);

    IconData volIcon;
    if (_state.isMuted || displayVol == 0) {
      volIcon = Icons.volume_off_rounded;
    } else if (displayVol < 40) {
      volIcon = Icons.volume_down_rounded;
    } else {
      volIcon = Icons.volume_up_rounded;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF111118),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.blueAccent.withAlpha(60),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              IconButton(
                icon: Icon(
                  volIcon,
                  color: _state.isMuted ? Colors.redAccent : Colors.blueAccent,
                ),
                onPressed: _toggleMute,
                tooltip: _state.isMuted ? 'Unmute' : 'Mute',
              ),
              Expanded(
                child: SliderTheme(
                  data: SliderTheme.of(context).copyWith(
                    activeTrackColor:
                        _state.isMuted ? Colors.grey[600] : Colors.blueAccent,
                    thumbColor: Colors.white,
                    overlayColor: Colors.blueAccent.withAlpha(40),
                  ),
                  child: Slider(
                    value: sliderVal,
                    min: 0,
                    max: 100,
                    divisions: 20,
                    label: '$displayVol%',
                    onChanged: _onVolumeChanged,
                    onChangeEnd: _onVolumeChangeEnd,
                  ),
                ),
              ),
              SizedBox(
                width: 44,
                child: Text(
                  '$displayVol%',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                  textAlign: TextAlign.end,
                ),
              ),
            ],
          ),
          // Step buttons row
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _stepBtn(Icons.remove_rounded, _controller.volumeDown, 'Vol −'),
              const SizedBox(width: 32),
              _stepBtn(Icons.add_rounded, _controller.volumeUp, 'Vol +'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _stepBtn(IconData icon, VoidCallback fn, String tip) =>
      IconButton(
        icon: Icon(icon, color: Colors.blueAccent),
        onPressed: fn,
        tooltip: tip,
        style: IconButton.styleFrom(
          backgroundColor: const Color(0xFF1A1A2E),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: const BorderSide(color: Colors.blueAccent, width: 1),
          ),
        ),
      );
}
