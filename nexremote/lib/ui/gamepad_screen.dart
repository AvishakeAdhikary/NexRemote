import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/gamepad_controller.dart';

// Re-export so callers only need this file
export '../input/gamepad_controller.dart';

class GamepadScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const GamepadScreen({super.key, required this.connectionManager});

  @override
  State<GamepadScreen> createState() => _GamepadScreenState();
}

class _GamepadScreenState extends State<GamepadScreen>
    with SingleTickerProviderStateMixin {
  late GamepadController _ctrl;
  StreamSubscription? _gyroSub;

  bool _gyroEnabled = false;
  bool _loading = true;
  Offset _leftStick = Offset.zero;
  Offset _rightStick = Offset.zero;

  // Button press state for visual feedback
  final Set<String> _pressedButtons = {};

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _ctrl = GamepadController(widget.connectionManager);
    _ctrl.loadPresets().then((_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _gyroEnabled = _ctrl.activeLayout.gyroEnabled;
          if (_gyroEnabled) _startGyro();
        });
      }
    });
  }

  @override
  void dispose() {
    _gyroSub?.cancel();
    _ctrl.dispose();
    super.dispose();
  }

  // ── Gyroscope ─────────────────────────────────────────────────────────────

  void _startGyro() {
    _gyroSub = gyroscopeEventStream().listen((GyroscopeEvent e) {
      _ctrl.sendGyroData(e.x, e.y, e.z);
    });
  }

  void _stopGyro() {
    _gyroSub?.cancel();
    _gyroSub = null;
  }

  // ── Settings bottom sheet ─────────────────────────────────────────────────

  void _openSettings() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _GamepadSettingsSheet(
        ctrl: _ctrl,
        gyroEnabled: _gyroEnabled,
        onApply: (layout, gyro) async {
          await _ctrl.applyLayout(layout);
          setState(() {
            _gyroEnabled = gyro;
          });
          if (gyro) {
            _startGyro();
          } else {
            _stopGyro();
          }
        },
      ),
    );
  }

  // ── Button helpers ────────────────────────────────────────────────────────

  String _label(String key) => _ctrl.activeLayout.buttons[key]?.label ?? key;

  Color _color(String key, Color def) {
    final cfg = _ctrl.activeLayout.buttons[key];
    return cfg != null ? Color(cfg.colorValue) : def;
  }

  void _press(String key) {
    setState(() => _pressedButtons.add(key));
    _ctrl.sendButton(key, true);
  }

  void _release(String key) {
    setState(() => _pressedButtons.remove(key));
    _ctrl.sendButton(key, false);
  }

  void _dpadPress(String dir) {
    setState(() => _pressedButtons.add('dpad_$dir'));
    _ctrl.sendDPad(dir, true);
  }

  void _dpadRelease(String dir) {
    setState(() => _pressedButtons.remove('dpad_$dir'));
    _ctrl.sendDPad(dir, false);
  }

  bool _isPressed(String key) => _pressedButtons.contains(key);

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Color(0xFF111827),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final layout = _ctrl.activeLayout;
    final isLandscape =
        MediaQuery.of(context).orientation == Orientation.landscape;

    return Scaffold(
      backgroundColor: const Color(0xFF111827),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1F2937),
        foregroundColor: Colors.white,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Gamepad',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            Text(
              '${layout.name}  •  ${layout.mode.label}',
              style: const TextStyle(fontSize: 11, color: Colors.white60),
            ),
          ],
        ),
        actions: [
          // Gyro toggle
          IconButton(
            tooltip: _gyroEnabled ? 'Gyro ON' : 'Gyro OFF',
            icon: Icon(
              _gyroEnabled
                  ? Icons.screen_rotation_alt
                  : Icons.screen_rotation_alt_outlined,
              color: _gyroEnabled ? Colors.tealAccent : Colors.white54,
            ),
            onPressed: () {
              setState(() => _gyroEnabled = !_gyroEnabled);
              if (_gyroEnabled) {
                _startGyro();
              } else {
                _stopGyro();
              }
            },
          ),
          // Settings
          IconButton(
            tooltip: 'Gamepad Settings',
            icon: const Icon(Icons.tune),
            onPressed: _openSettings,
          ),
        ],
      ),
      body: SafeArea(child: isLandscape ? _buildLandscape() : _buildPortrait()),
    );
  }

  // ── Layouts ───────────────────────────────────────────────────────────────

  Widget _buildPortrait() {
    return Column(
      children: [
        _buildShoulderRow(),
        Expanded(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [_buildDPad(), _buildJoystick(isLeft: true)],
                ),
              ),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _buildActionButtons(),
                    _buildJoystick(isLeft: false),
                  ],
                ),
              ),
            ],
          ),
        ),
        _buildCenterButtons(),
        const SizedBox(height: 12),
      ],
    );
  }

  Widget _buildLandscape() {
    return Stack(
      children: [
        // Left zone
        Positioned(
          left: 16,
          top: 0,
          bottom: 0,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildShoulderPair(isLeft: true),
              _buildDPad(),
              _buildJoystick(isLeft: true),
            ],
          ),
        ),
        // Centre
        Positioned(
          left: 0,
          right: 0,
          bottom: 12,
          child: Center(child: _buildCenterButtons()),
        ),
        // Right zone
        Positioned(
          right: 16,
          top: 0,
          bottom: 0,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildShoulderPair(isLeft: false),
              _buildActionButtons(),
              _buildJoystick(isLeft: false),
            ],
          ),
        ),
      ],
    );
  }

  // ── Component widgets ─────────────────────────────────────────────────────

  Widget _buildShoulderRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _buildShoulderPair(isLeft: true),
          _buildShoulderPair(isLeft: false),
        ],
      ),
    );
  }

  Widget _buildShoulderPair({required bool isLeft}) {
    final lb = isLeft ? 'L1' : 'R1';
    final lt = isLeft ? 'L2' : 'R2';
    return Column(
      children: [
        _buildShoulderBtn(lb),
        const SizedBox(height: 4),
        _buildShoulderBtn(lt),
      ],
    );
  }

  Widget _buildShoulderBtn(String key) {
    final pressed = _isPressed(key);
    return GestureDetector(
      onTapDown: (_) => _press(key),
      onTapUp: (_) => _release(key),
      onTapCancel: () => _release(key),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 80),
        width: 64,
        height: 32,
        decoration: BoxDecoration(
          color: pressed ? Colors.blueAccent : const Color(0xFF374151),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: pressed ? Colors.blueAccent : Colors.white24,
          ),
          boxShadow: pressed
              ? [const BoxShadow(color: Colors.blueAccent, blurRadius: 8)]
              : [],
        ),
        child: Center(
          child: Text(
            _label(key),
            style: TextStyle(
              color: pressed ? Colors.white : Colors.white70,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDPad() {
    return SizedBox(
      width: 120,
      height: 120,
      child: Stack(
        children: [
          _dpadBtn('UP', Icons.arrow_drop_up, top: 0, left: 40),
          _dpadBtn('DOWN', Icons.arrow_drop_down, bottom: 0, left: 40),
          _dpadBtn('LEFT', Icons.arrow_left, top: 40, left: 0),
          _dpadBtn('RIGHT', Icons.arrow_right, top: 40, right: 0),
          // Centre nub
          const Positioned(
            left: 42,
            top: 42,
            child: SizedBox(
              width: 36,
              height: 36,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Color(0xFF374151),
                  shape: BoxShape.circle,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _dpadBtn(
    String dir,
    IconData icon, {
    double? top,
    double? bottom,
    double? left,
    double? right,
  }) {
    final pressed = _isPressed('dpad_$dir');
    return Positioned(
      top: top,
      bottom: bottom,
      left: left,
      right: right,
      child: GestureDetector(
        onTapDown: (_) => _dpadPress(dir),
        onTapUp: (_) => _dpadRelease(dir),
        onTapCancel: () => _dpadRelease(dir),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 70),
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: pressed ? Colors.blueAccent : const Color(0xFF374151),
            border: Border.all(
              color: pressed ? Colors.blueAccent : Colors.white24,
            ),
          ),
          child: Icon(
            icon,
            color: pressed ? Colors.white : Colors.white60,
            size: 24,
          ),
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return SizedBox(
      width: 120,
      height: 120,
      child: Stack(
        children: [
          Positioned(
            top: 0,
            left: 40,
            child: _actionBtn('Y', def: const Color(0xFFF59E0B)),
          ),
          Positioned(
            bottom: 0,
            left: 40,
            child: _actionBtn('A', def: const Color(0xFF10B981)),
          ),
          Positioned(
            left: 0,
            top: 40,
            child: _actionBtn('X', def: const Color(0xFF3B82F6)),
          ),
          Positioned(
            right: 0,
            top: 40,
            child: _actionBtn('B', def: const Color(0xFFEF4444)),
          ),
        ],
      ),
    );
  }

  Widget _actionBtn(String key, {required Color def}) {
    final color = _color(key, def);
    final pressed = _isPressed(key);
    return GestureDetector(
      onTapDown: (_) => _press(key),
      onTapUp: (_) => _release(key),
      onTapCancel: () => _release(key),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 70),
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: pressed ? color : color.withAlpha(70),
          shape: BoxShape.circle,
          border: Border.all(color: color, width: 2),
          boxShadow: pressed
              ? [BoxShadow(color: color.withAlpha(180), blurRadius: 10)]
              : [],
        ),
        child: Center(
          child: Text(
            _label(key),
            style: TextStyle(
              color: pressed ? Colors.white : color,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildJoystick({required bool isLeft}) {
    final offset = isLeft ? _leftStick : _rightStick;
    const size = 100.0;
    const nubSize = 34.0;
    const radius = (size - nubSize) / 2;

    return GestureDetector(
      onPanStart: (_) {},
      onPanUpdate: (d) => _updateStick(d.localPosition, isLeft, size),
      onPanEnd: (_) => _releaseStick(isLeft),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: const Color(0xFF1F2937),
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white24, width: 1.5),
        ),
        child: Stack(
          children: [
            // Track ring
            Center(
              child: Container(
                width: size - 20,
                height: size - 20,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white10, width: 1),
                ),
              ),
            ),
            // Nub
            Positioned(
              left: size / 2 + offset.dx * radius - nubSize / 2,
              top: size / 2 + offset.dy * radius - nubSize / 2,
              child: Container(
                width: nubSize,
                height: nubSize,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF60A5FA), Color(0xFF3B82F6)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF3B82F6).withAlpha(150),
                      blurRadius: 8,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _updateStick(Offset pos, bool isLeft, double size) {
    final center = Offset(size / 2, size / 2);
    var delta = pos - center;
    final dist = delta.distance;
    final maxDist = size / 2 - 17;
    if (dist > maxDist) delta = delta * (maxDist / dist);
    final norm = Offset(delta.dx / maxDist, delta.dy / maxDist);

    setState(() {
      if (isLeft) {
        _leftStick = norm;
      } else {
        _rightStick = norm;
      }
    });
    _ctrl.sendJoystick(isLeft ? 'left' : 'right', norm.dx, -norm.dy);
  }

  void _releaseStick(bool isLeft) {
    setState(() {
      if (isLeft) {
        _leftStick = Offset.zero;
      } else {
        _rightStick = Offset.zero;
      }
    });
    _ctrl.sendJoystick(isLeft ? 'left' : 'right', 0, 0);
  }

  Widget _buildCenterButtons() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _centerBtn('SELECT', Icons.view_stream),
        const SizedBox(width: 32),
        _centerBtn('START', Icons.play_arrow),
      ],
    );
  }

  Widget _centerBtn(String key, IconData icon) {
    final pressed = _isPressed(key);
    return GestureDetector(
      onTapDown: (_) => _press(key),
      onTapUp: (_) => _release(key),
      onTapCancel: () => _release(key),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 80),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
        decoration: BoxDecoration(
          color: pressed ? Colors.blueAccent : const Color(0xFF374151),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: pressed ? Colors.blueAccent : Colors.white24,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, size: 14, color: Colors.white70),
            const SizedBox(width: 4),
            Text(
              _label(key),
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Settings bottom sheet ──────────────────────────────────────────────────────

class _GamepadSettingsSheet extends StatefulWidget {
  final GamepadController ctrl;
  final bool gyroEnabled;
  final Future<void> Function(GamepadLayout layout, bool gyro) onApply;

  const _GamepadSettingsSheet({
    required this.ctrl,
    required this.gyroEnabled,
    required this.onApply,
  });

  @override
  State<_GamepadSettingsSheet> createState() => _GamepadSettingsSheetState();
}

class _GamepadSettingsSheetState extends State<_GamepadSettingsSheet> {
  late GamepadLayout _draft;
  late bool _gyro;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _draft = widget.ctrl.activeLayout;
    _gyro = widget.gyroEnabled;
  }

  Future<void> _apply() async {
    setState(() => _saving = true);
    // For built-ins: create a patched copy if haptic/gyro changed
    GamepadLayout toApply = _draft;
    if (_draft.isBuiltIn &&
        (_draft.hapticFeedback != widget.ctrl.hapticEnabled ||
            _gyro != widget.gyroEnabled)) {
      toApply = _draft.copyWith(
        hapticFeedback: _draft.hapticFeedback,
        gyroEnabled: _gyro,
      );
    }
    await widget.onApply(toApply, _gyro);
    if (mounted) Navigator.pop(context);
  }

  Future<void> _saveAsNew() async {
    final name = await _promptName(context, 'Save as Preset');
    if (name == null || name.isEmpty) return;
    final newLayout = GamepadLayout(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      name: name,
      mode: _draft.mode,
      hapticFeedback: _draft.hapticFeedback,
      gyroEnabled: _gyro,
      buttons: _draft.buttons,
    );
    await widget.ctrl.saveCustomLayout(newLayout);
    if (mounted) setState(() {});
  }

  Future<String?> _promptName(BuildContext ctx, String title) async {
    String value = '';
    return showDialog<String>(
      context: ctx,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: TextField(
          autofocus: true,
          decoration: const InputDecoration(hintText: 'Preset name'),
          onChanged: (v) => value = v,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, value),
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final presets = widget.ctrl.presetManager.all;

    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      minChildSize: 0.4,
      maxChildSize: 0.92,
      builder: (_, scroll) => Container(
        decoration: const BoxDecoration(
          color: Color(0xFF1F2937),
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: ListView(
          controller: scroll,
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: [
            // Handle bar
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Title
            const Text(
              'Gamepad Settings',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),

            // ── Mode selector ────────────────────────────────────────────
            const Text(
              'Input Mode',
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 8),
            SegmentedButton<GamepadMode>(
              style: SegmentedButton.styleFrom(
                backgroundColor: const Color(0xFF374151),
                selectedBackgroundColor: Colors.blueAccent,
                foregroundColor: Colors.white70,
                selectedForegroundColor: Colors.white,
              ),
              segments: GamepadMode.values
                  .map(
                    (m) => ButtonSegment(
                      value: m,
                      label: Text(m.label),
                      tooltip: m.description,
                    ),
                  )
                  .toList(),
              selected: {_draft.mode},
              onSelectionChanged: (s) =>
                  setState(() => _draft = _draft.copyWith(mode: s.first)),
            ),
            Padding(
              padding: const EdgeInsets.only(top: 6, bottom: 16),
              child: Text(
                _draft.mode.description,
                style: const TextStyle(color: Colors.white38, fontSize: 12),
              ),
            ),

            // ── Haptic feedback ──────────────────────────────────────────
            _settingsTile(
              title: 'Haptic Feedback',
              subtitle: 'Vibrate on button press',
              trailing: Switch(
                value: _draft.hapticFeedback,
                onChanged: (v) =>
                    setState(() => _draft = _draft.copyWith(hapticFeedback: v)),
                activeThumbColor: Colors.blueAccent,
              ),
            ),

            // ── Gyroscope ────────────────────────────────────────────────
            _settingsTile(
              title: 'Gyroscope',
              subtitle: 'Send gyro data as joystick tilt',
              trailing: Switch(
                value: _gyro,
                onChanged: (v) => setState(() => _gyro = v),
                activeThumbColor: Colors.tealAccent,
              ),
            ),

            const Divider(color: Colors.white12, height: 32),

            // ── Presets ──────────────────────────────────────────────────
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Presets',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                TextButton.icon(
                  onPressed: _saveAsNew,
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text('Save current'),
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.blueAccent,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ...presets.map((p) => _presetTile(p)),

            const SizedBox(height: 24),

            // ── Apply / Cancel ───────────────────────────────────────────
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white54,
                    ),
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _saving ? null : _apply,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blueAccent,
                    ),
                    child: _saving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Apply'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _presetTile(GamepadLayout p) {
    final isActive = p.id == widget.ctrl.activeLayout.id;
    final isCustom = !p.isBuiltIn;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: isActive
            ? Colors.blueAccent.withAlpha(40)
            : const Color(0xFF374151),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isActive ? Colors.blueAccent : Colors.white12,
        ),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        title: Text(
          p.name,
          style: TextStyle(
            color: isActive ? Colors.blueAccent : Colors.white,
            fontWeight: FontWeight.w600,
          ),
        ),
        subtitle: Text(
          '${p.mode.label}  •  ${p.hapticFeedback ? "Haptic" : "No haptic"}',
          style: const TextStyle(color: Colors.white38, fontSize: 12),
        ),
        leading: Icon(
          isActive ? Icons.radio_button_checked : Icons.radio_button_unchecked,
          color: isActive ? Colors.blueAccent : Colors.white38,
        ),
        trailing: isCustom
            ? IconButton(
                icon: const Icon(
                  Icons.delete_outline,
                  color: Colors.redAccent,
                  size: 20,
                ),
                onPressed: () async {
                  await widget.ctrl.deleteCustomLayout(p);
                  setState(() {});
                },
              )
            : null,
        onTap: () {
          setState(() {
            _draft = p.copyWith(hapticFeedback: p.hapticFeedback);
            _gyro = p.gyroEnabled;
          });
        },
      ),
    );
  }

  Widget _settingsTile({
    required String title,
    required String subtitle,
    required Widget trailing,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF374151),
        borderRadius: BorderRadius.circular(12),
      ),
      child: ListTile(
        title: Text(
          title,
          style: const TextStyle(color: Colors.white, fontSize: 14),
        ),
        subtitle: Text(
          subtitle,
          style: const TextStyle(color: Colors.white38, fontSize: 12),
        ),
        trailing: trailing,
      ),
    );
  }
}
