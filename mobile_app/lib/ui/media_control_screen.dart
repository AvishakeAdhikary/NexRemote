import 'package:flutter/material.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/media_controller.dart';

class MediaControlScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const MediaControlScreen({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);

  @override
  State<MediaControlScreen> createState() => _MediaControlScreenState();
}

class _MediaControlScreenState extends State<MediaControlScreen> {
  late MediaController _controller;
  bool _isPlaying = false;
  bool _isMuted = false;
  int _volume = 50;
  double _seekPosition = 0.0;
  String _title = 'No Media Playing';
  String _artist = '';
  Duration _duration = Duration.zero;
  Duration _position = Duration.zero;

  Timer? _infoRefreshTimer;

  @override
  void initState() {
    super.initState();
    _controller = MediaController(widget.connectionManager);
    
    // Request media info periodically
    _infoRefreshTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      _controller.requestMediaInfo();
    });
    
    _controller.requestMediaInfo();
  }

  void _togglePlayPause() {
    if (_isPlaying) {
      _controller.pause();
      setState(() => _isPlaying = false);
    } else {
      _controller.play();
      setState(() => _isPlaying = true);
    }
  }

  void _stop() {
    _controller.stop();
    setState(() {
      _isPlaying = false;
      _position = Duration.zero;
    });
  }

  void _next() {
    _controller.next();
  }

  void _previous() {
    _controller.previous();
  }

  void _toggleMute() {
    _controller.toggleMute();
    setState(() => _isMuted = !_isMuted);
  }

  void _setVolume(int value) {
    setState(() => _volume = value);
    _controller.setVolume(value);
  }

  void _seek(double value) {
    _controller.seek(value);
    setState(() => _seekPosition = value);
  }

  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = duration.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final isLandscape = MediaQuery.of(context).orientation == Orientation.landscape;
    
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      appBar: AppBar(
        title: const Text('Media Control'),
      ),
      body: SafeArea(
        child: isLandscape
            ? _buildLandscapeLayout()
            : _buildPortraitLayout(),
      ),
    );
  }

  Widget _buildPortraitLayout() {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildAlbumArt(),
            const SizedBox(height: 24),
            _buildMediaInfo(),
            const SizedBox(height: 32),
            _buildSeekBar(),
            const SizedBox(height: 32),
            _buildPlaybackControls(),
            const SizedBox(height: 32),
            _buildVolumeControl(),
          ],
        ),
      ),
    );
  }

  Widget _buildLandscapeLayout() {
    return Row(
      children: [
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildAlbumArt(),
              const SizedBox(height: 16),
              _buildMediaInfo(),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildSeekBar(),
                const SizedBox(height: 24),
                _buildPlaybackControls(),
                const SizedBox(height: 24),
                _buildVolumeControl(),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAlbumArt() {
    return Container(
      width: 200,
      height: 200,
      decoration: BoxDecoration(
        color: Colors.grey[800],
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.blue, width: 2),
        boxShadow: [
          BoxShadow(
            color: Colors.blue.withOpacity(0.3),
            blurRadius: 20,
            spreadRadius: 5,
          ),
        ],
      ),
      child: Icon(
        Icons.music_note,
        size: 100,
        color: Colors.grey[600],
      ),
    );
  }

  Widget _buildMediaInfo() {
    return Column(
      children: [
        Text(
          _title,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
          textAlign: TextAlign.center,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        if (_artist.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            _artist,
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[400],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ],
    );
  }

  Widget _buildSeekBar() {
    return Column(
      children: [
        Slider(
          value: _seekPosition,
          min: 0.0,
          max: 1.0,
          onChanged: _seek,
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _formatDuration(_position),
                style: TextStyle(color: Colors.grey[400], fontSize: 12),
              ),
              Text(
                _formatDuration(_duration),
                style: TextStyle(color: Colors.grey[400], fontSize: 12),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPlaybackControls() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _buildControlButton(
          Icons.skip_previous,
          _previous,
          60,
        ),
        const SizedBox(width: 20),
        _buildControlButton(
          _isPlaying ? Icons.pause : Icons.play_arrow,
          _togglePlayPause,
          80,
          isPrimary: true,
        ),
        const SizedBox(width: 20),
        _buildControlButton(
          Icons.skip_next,
          _next,
          60,
        ),
      ],
    );
  }

  Widget _buildControlButton(
    IconData icon,
    VoidCallback onTap,
    double size, {
    bool isPrimary = false,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: isPrimary ? Colors.blue : Colors.grey[800],
          shape: BoxShape.circle,
          border: Border.all(
            color: isPrimary ? Colors.blue[300]! : Colors.blue,
            width: 2,
          ),
          boxShadow: isPrimary
              ? [
                  BoxShadow(
                    color: Colors.blue.withOpacity(0.5),
                    blurRadius: 15,
                    spreadRadius: 2,
                  ),
                ]
              : null,
        ),
        child: Icon(
          icon,
          size: size * 0.5,
          color: Colors.white,
        ),
      ),
    );
  }

  Widget _buildVolumeControl() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.withOpacity(0.3), width: 1),
      ),
      child: Column(
        children: [
          Row(
            children: [
              IconButton(
                icon: Icon(
                  _isMuted ? Icons.volume_off : Icons.volume_up,
                  color: _isMuted ? Colors.red : Colors.blue,
                ),
                onPressed: _toggleMute,
              ),
              Expanded(
                child: Slider(
                  value: _volume.toDouble(),
                  min: 0,
                  max: 100,
                  divisions: 20,
                  label: '$_volume%',
                  onChanged: (value) => _setVolume(value.round()),
                ),
              ),
              Text(
                '$_volume%',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(width: 8),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.stop, color: Colors.red),
                onPressed: _stop,
                tooltip: 'Stop',
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _infoRefreshTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }
}
