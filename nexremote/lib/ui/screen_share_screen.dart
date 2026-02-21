import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:typed_data';
import '../core/connection_manager.dart';
import '../input/screen_share_controller.dart';

class ScreenShareScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const ScreenShareScreen({
    super.key,
    required this.connectionManager,
  });

  @override
  State<ScreenShareScreen> createState() => _ScreenShareScreenState();
}

class _ScreenShareScreenState extends State<ScreenShareScreen>
    with TickerProviderStateMixin {
  late ScreenShareController _ctrl;

  // ── Display list ─────────────────────────────────────────────────────────
  List<DisplayInfo> _displays = [];
  /// Monitor indices the user has selected to stream
  final Set<int> _selectedIndices = {0};

  // ── Streaming state ──────────────────────────────────────────────────────
  bool _isStreaming = false;
  bool _interactiveMode = false;

  // Per-monitor frame buffers  {displayIndex: latestJpegBytes}
  final Map<int, Uint8List> _frames = {};
  final Map<int, StreamSubscription<Uint8List>> _frameSubs = {};

  // Per-monitor FPS counters
  final Map<int, double> _fpsCounts = {};
  final Map<int, DateTime> _lastFrameTimes = {};

  // TabController for multi-monitor tab view
  TabController? _tabCtrl;

  // ── Settings ─────────────────────────────────────────────────────────────
  int _fps = 30;
  String _quality = 'medium';
  String _resolution = 'native';

  // Controls panel visibility while streaming
  bool _optionsVisible = false;

  // Display subscriptions
  StreamSubscription? _displaysSub;

  // For coordinate mapping on interactive screen
  final GlobalKey _imageKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _ctrl = ScreenShareController(widget.connectionManager);

    _displaysSub = _ctrl.displaysStream.listen((displays) {
      if (!mounted) return;
      setState(() {
        _displays = displays;
        // Rebuild tab controller when display count changes
        _rebuildTabController();
      });
    });

    _ctrl.requestDisplayList();
  }

  void _rebuildTabController() {
    final count = (_isStreaming && _selectedIndices.isNotEmpty)
        ? _selectedIndices.length
        : 1;
    _tabCtrl?.dispose();
    _tabCtrl = TabController(length: count, vsync: this);
  }

  // ── Streaming lifecycle ──────────────────────────────────────────────────

  void _startStreaming() {
    final indices = _selectedIndices.toList()..sort();

    // Subscribe to per-monitor frame streams
    for (final idx in indices) {
      _frameSubs[idx]?.cancel();
      _frameSubs[idx] = _ctrl.frameStreamForMonitor(idx).listen((jpeg) {
        if (!mounted) return;
        final now = DateTime.now();
        setState(() {
          _frames[idx] = jpeg;
          final last = _lastFrameTimes[idx];
          if (last != null) {
            final ms = now.difference(last).inMilliseconds;
            if (ms > 0) { _fpsCounts[idx] = 1000.0 / ms; }
          }
          _lastFrameTimes[idx] = now;
        });
      });
    }

    _ctrl.startStreaming(
      displayIndices: indices,
      fps: _fps,
      quality: _quality,
      resolution: _resolution,
    );

    setState(() {
      _isStreaming = true;
      _optionsVisible = false;   // hide options when streaming starts
      _rebuildTabController();
    });
  }

  void _stopStreaming() {
    for (final sub in _frameSubs.values) { sub.cancel(); }
    _frameSubs.clear();
    _ctrl.stopStreaming();

    setState(() {
      _isStreaming = false;
      _interactiveMode = false;
      _frames.clear();
      _fpsCounts.clear();
      _optionsVisible = false;
      _rebuildTabController();
    });
  }

  // (tab monitor index resolved inline in _buildMonitorView callers)

  // ── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: _buildAppBar(),
      body: SafeArea(child: _buildBody()),
    );
  }

  AppBar _buildAppBar() {
    return AppBar(
      backgroundColor: const Color(0xFF0D0D0F),
      foregroundColor: Colors.white,
      elevation: 0,
      title: const Text('Screen Share'),
      actions: [
        // Interactive mode toggle (only while streaming)
        if (_isStreaming)
          IconButton(
            icon: Icon(
              _interactiveMode ? Icons.touch_app : Icons.pan_tool_alt,
              color: _interactiveMode ? Colors.greenAccent : Colors.white70,
            ),
            tooltip: _interactiveMode
                ? 'Interactive ON — tap to disable'
                : 'Enable interactive mode',
            onPressed: () =>
                setState(() => _interactiveMode = !_interactiveMode),
          ),
        // Settings / options reveal
        IconButton(
          icon: Icon(
            _isStreaming ? Icons.tune : Icons.settings,
            color: _optionsVisible ? Colors.blueAccent : Colors.white70,
          ),
          tooltip: 'Stream options',
          onPressed: () =>
              setState(() => _optionsVisible = !_optionsVisible),
        ),
      ],
    );
  }

  Widget _buildBody() {
    return Column(
      children: [
        // ── OPTIONS PANEL (hidden during streaming unless revealed) ─────────
        AnimatedSize(
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeInOut,
          child: (!_isStreaming || _optionsVisible)
              ? _buildOptionsPanel()
              : const SizedBox.shrink(),
        ),

        // ── SCREEN AREA ─────────────────────────────────────────────────────
        Expanded(child: _buildScreenArea()),

        // ── START / STOP BUTTON ─────────────────────────────────────────────
        _buildStartStopBar(),
      ],
    );
  }

  // ── Options panel ─────────────────────────────────────────────────────────

  Widget _buildOptionsPanel() {
    return Container(
      color: const Color(0xFF111118),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Monitor selection (multi-select chips)
          if (_displays.isNotEmpty) ...[
            Row(
              children: [
                const Icon(Icons.monitor, size: 18, color: Colors.blueAccent),
                const SizedBox(width: 8),
                const Text(
                  'Displays',
                  style: TextStyle(
                    color: Colors.white70, fontWeight: FontWeight.w600),
                ),
                const SizedBox(width: 8),
                Text(
                  '(select one or more)',
                  style: TextStyle(color: Colors.grey[600], fontSize: 11),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: _displays.map((d) {
                final selected = _selectedIndices.contains(d.index);
                return FilterChip(
                  label: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(d.name,
                          style: TextStyle(
                            color: selected ? Colors.white : Colors.grey[400],
                            fontWeight: FontWeight.w600,
                            fontSize: 12,
                          )),
                      Text(d.resolution,
                          style: TextStyle(
                            color: selected
                                ? Colors.blue[200]
                                : Colors.grey[600],
                            fontSize: 10,
                          )),
                    ],
                  ),
                  selected: selected,
                  onSelected: _isStreaming
                      ? null   // lock during streaming (user can reveal options to see but not change displays mid-stream)
                      : (sel) {
                          setState(() {
                            if (sel) {
                              _selectedIndices.add(d.index);
                            } else if (_selectedIndices.length > 1) {
                              _selectedIndices.remove(d.index);
                            }
                          });
                        },
                  selectedColor: Colors.blueAccent.withAlpha(80),
                  checkmarkColor: Colors.blueAccent,
                  backgroundColor: const Color(0xFF1A1A2E),
                  side: BorderSide(
                    color: selected ? Colors.blueAccent : Colors.grey[700]!,
                  ),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4),
                );
              }).toList(),
            ),
            const Divider(color: Color(0xFF2A2A3A), height: 20),
          ],

          // Resolution
          Row(
            children: [
              const Icon(Icons.aspect_ratio, size: 18, color: Colors.blueAccent),
              const SizedBox(width: 8),
              const SizedBox(
                width: 60,
                child: Text('Res:',
                    style: TextStyle(color: Colors.white70)),
              ),
              Expanded(
                child: SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'native', label: Text('Native')),
                    ButtonSegment(value: '1080p',  label: Text('1080p')),
                    ButtonSegment(value: '720p',   label: Text('720p')),
                    ButtonSegment(value: '480p',   label: Text('480p')),
                  ],
                  selected: {_resolution},
                  onSelectionChanged: (s) {
                    setState(() => _resolution = s.first);
                    if (_isStreaming) _ctrl.setResolution(_resolution);
                  },
                  style: const ButtonStyle(
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Quality
          Row(
            children: [
              const Icon(Icons.high_quality, size: 18, color: Colors.blueAccent),
              const SizedBox(width: 8),
              const SizedBox(
                width: 60,
                child: Text('Quality:',
                    style: TextStyle(color: Colors.white70)),
              ),
              Expanded(
                child: SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'low',    label: Text('Low')),
                    ButtonSegment(value: 'medium', label: Text('Med')),
                    ButtonSegment(value: 'high',   label: Text('High')),
                    ButtonSegment(value: 'ultra',  label: Text('Ultra')),
                  ],
                  selected: {_quality},
                  onSelectionChanged: (s) {
                    setState(() => _quality = s.first);
                    if (_isStreaming) {
                      const map = {
                        'low': 30, 'medium': 50, 'high': 70, 'ultra': 90
                      };
                      _ctrl.setQuality(map[_quality]!);
                    }
                  },
                  style: const ButtonStyle(
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 4),

          // FPS
          Row(
            children: [
              const Icon(Icons.speed, size: 18, color: Colors.blueAccent),
              const SizedBox(width: 8),
              SizedBox(
                width: 60,
                child: Text('FPS: $_fps',
                    style: const TextStyle(color: Colors.white70)),
              ),
              Expanded(
                child: Slider(
                  value: _fps.toDouble(),
                  min: 5, max: 60, divisions: 11,
                  label: '$_fps',
                  activeColor: Colors.blueAccent,
                  onChanged: (v) => setState(() => _fps = v.round()),
                  onChangeEnd: (v) {
                    if (_isStreaming) _ctrl.setFps(v.round());
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ── Screen area ──────────────────────────────────────────────────────────

  Widget _buildScreenArea() {
    if (!_isStreaming) return _buildIdleScreen();

    final sorted = _selectedIndices.toList()..sort();
    if (sorted.length == 1) {
      // Single monitor — full-screen view
      return _buildMonitorView(sorted.first);
    }

    // Multi-monitor — tabs
    if (_tabCtrl == null || _tabCtrl!.length != sorted.length) {
      _rebuildTabController();
    }

    return Column(
      children: [
        TabBar(
          controller: _tabCtrl,
          isScrollable: true,
          labelColor: Colors.blueAccent,
          unselectedLabelColor: Colors.grey,
          indicatorColor: Colors.blueAccent,
          tabs: sorted.map((idx) {
            final disp = _displays.firstWhere(
              (d) => d.index == idx,
              orElse: () => DisplayInfo(
                  index: idx, name: 'Display ${idx + 1}',
                  width: 1920, height: 1080),
            );
            final fps = _fpsCounts[idx]?.toStringAsFixed(1) ?? '…';
            return Tab(
              icon: const Icon(Icons.monitor, size: 16),
              text: '${disp.name}  $fps fps',
            );
          }).toList(),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabCtrl,
            children: sorted
                .map((idx) => _buildMonitorView(idx))
                .toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildIdleScreen() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.screen_share_outlined, size: 80, color: Colors.grey[700]),
          const SizedBox(height: 20),
          Text(
            'Not Streaming',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: Colors.grey[400],
            ),
          ),
          const SizedBox(height: 10),
          Text(
            _selectedIndices.length > 1
                ? 'Tap Start to stream ${_selectedIndices.length} displays'
                : 'Tap Start Streaming to view your PC screen',
            style: TextStyle(fontSize: 14, color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildMonitorView(int monitorIndex) {
    final frame = _frames[monitorIndex];

    if (frame == null) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: Colors.blueAccent),
            SizedBox(height: 14),
            Text('Waiting for frames…',
                style: TextStyle(color: Colors.white54)),
          ],
        ),
      );
    }

    return Stack(
      children: [
        _interactiveMode
            ? _buildInteractive(frame, monitorIndex)
            : _buildViewOnly(frame),

        // LIVE badge
        Positioned(
          top: 12, left: 12,
          child: _badge('● LIVE', Colors.greenAccent, Colors.green[900]!),
        ),

        // FPS + mode overlay
        Positioned(
          top: 12, right: 12,
          child: _badge(
            _interactiveMode
                ? 'INTERACTIVE'
                : '${_fpsCounts[monitorIndex]?.toStringAsFixed(1) ?? "…"} fps'
                  '  $_resolution  $_quality',
            _interactiveMode ? Colors.greenAccent : Colors.white,
            _interactiveMode
                ? Colors.green[900]!
                : Colors.black54,
          ),
        ),
      ],
    );
  }

  Widget _badge(String text, Color fg, Color bg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(text,
            style: TextStyle(
                color: fg, fontWeight: FontWeight.bold, fontSize: 11)),
      );

  Widget _buildViewOnly(Uint8List frame) => InteractiveViewer(
        minScale: 0.5,
        maxScale: 5.0,
        child: Container(
          margin: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.greenAccent.withAlpha(120), width: 2),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: Image.memory(frame,
                fit: BoxFit.contain, gaplessPlayback: true),
          ),
        ),
      );

  Widget _buildInteractive(Uint8List frame, int monIdx) {
    return Container(
      margin: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.greenAccent, width: 2),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(6),
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTapUp: (d) {
            final r = _rel(d.localPosition);
            if (r != null) _ctrl.sendTap(r.dx, r.dy, monitorIndex: monIdx);
          },
          onDoubleTapDown: (d) {
            final r = _rel(d.localPosition);
            if (r != null) _ctrl.sendDoubleTap(r.dx, r.dy, monitorIndex: monIdx);
          },
          onLongPressStart: (d) {
            final r = _rel(d.localPosition);
            if (r != null) _ctrl.sendRightClick(r.dx, r.dy, monitorIndex: monIdx);
          },
          onPanStart: (d) {
            final r = _rel(d.localPosition);
            if (r != null) _ctrl.sendMouseDown(r.dx, r.dy, monitorIndex: monIdx);
          },
          onPanUpdate: (d) {
            final r = _rel(d.localPosition);
            if (r != null) _ctrl.sendMouseMove(r.dx, r.dy, monitorIndex: monIdx);
          },
          onPanEnd: (_) =>
              _ctrl.sendMouseUp(0.5, 0.5, monitorIndex: monIdx),
          child: Image.memory(
            key: _imageKey,
            frame, fit: BoxFit.contain, gaplessPlayback: true,
          ),
        ),
      ),
    );
  }

  Offset? _rel(Offset local) {
    final box = _imageKey.currentContext?.findRenderObject() as RenderBox?;
    if (box == null) return null;
    final s = box.size;
    return Offset(
      (local.dx / s.width).clamp(0.0, 1.0),
      (local.dy / s.height).clamp(0.0, 1.0),
    );
  }

  // ── Start / Stop bar ─────────────────────────────────────────────────────

  Widget _buildStartStopBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        color: Color(0xFF0D0D0F),
        border: Border(top: BorderSide(color: Color(0xFF2A2A3A))),
      ),
      child: Row(
        children: [
          // Quick-options reveal hint when streaming
          if (_isStreaming) ...[
            Icon(Icons.tune, color: Colors.grey[600], size: 16),
            const SizedBox(width: 6),
            Text('Tap ⚙ to adjust',
                style: TextStyle(color: Colors.grey[600], fontSize: 12)),
            const Spacer(),
          ] else ...[
            // Display count hint
            Icon(Icons.monitor, color: Colors.grey[600], size: 16),
            const SizedBox(width: 6),
            Text(
              '${_selectedIndices.length} display${_selectedIndices.length > 1 ? "s" : ""} selected',
              style: TextStyle(color: Colors.grey[500], fontSize: 12),
            ),
            const Spacer(),
          ],
          SizedBox(
            height: 44,
            child: ElevatedButton.icon(
              onPressed: _isStreaming ? _stopStreaming : _startStreaming,
              icon: Icon(_isStreaming ? Icons.stop_rounded : Icons.play_arrow_rounded),
              label: Text(_isStreaming ? 'Stop' : 'Start Streaming',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(
                backgroundColor:
                    _isStreaming ? Colors.redAccent : Colors.blueAccent,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    for (final s in _frameSubs.values) { s.cancel(); }
    _frameSubs.clear();
    _displaysSub?.cancel();
    _tabCtrl?.dispose();
    _ctrl.dispose();
    super.dispose();
  }
}
