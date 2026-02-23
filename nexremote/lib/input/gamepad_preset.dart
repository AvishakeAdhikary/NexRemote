import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ── Gamepad mode ──────────────────────────────────────────────────────────────

enum GamepadMode {
  xinput('XInput', 'Xbox controller — best for PC games'),
  dinput('DInput', 'DualShock 4 style — for older games'),
  android('Android', 'Native Android gamepad — no PC emulation');

  const GamepadMode(this.label, this.description);
  final String label;
  final String description;
}

// ── Per-button style override ─────────────────────────────────────────────────

class ButtonConfig {
  final String label;
  final int colorValue; // ARGB

  const ButtonConfig({required this.label, required this.colorValue});

  factory ButtonConfig.fromJson(Map<String, dynamic> j) =>
      ButtonConfig(label: j['label'] as String, colorValue: j['color'] as int);

  Map<String, dynamic> toJson() => {'label': label, 'color': colorValue};
}

// ── Layout preset model ──────────────────────────────────────────────────────

class GamepadLayout {
  static const _defaultButtons = <String, ButtonConfig>{};

  final String id;
  final String name;
  final GamepadMode mode;
  final bool hapticFeedback;
  final bool gyroEnabled;
  final Map<String, ButtonConfig> buttons; // key = canonical button name

  const GamepadLayout({
    required this.id,
    required this.name,
    this.mode = GamepadMode.xinput,
    this.hapticFeedback = true,
    this.gyroEnabled = false,
    this.buttons = _defaultButtons,
  });

  // Built-in presets ────────────────────────────────────────────────────────

  static final GamepadLayout defaultXInput = GamepadLayout(
    id: '__default_xinput__',
    name: 'Default XInput',
    mode: GamepadMode.xinput,
    hapticFeedback: true,
  );

  static final GamepadLayout defaultDInput = GamepadLayout(
    id: '__default_dinput__',
    name: 'Default DInput',
    mode: GamepadMode.dinput,
    hapticFeedback: true,
    buttons: {
      'A': const ButtonConfig(label: '✕', colorValue: 0xFF5B9BD5),
      'B': const ButtonConfig(label: '○', colorValue: 0xFFE74C3C),
      'X': const ButtonConfig(label: '□', colorValue: 0xFF9B59B6),
      'Y': const ButtonConfig(label: '△', colorValue: 0xFF2ECC71),
    },
  );

  static final GamepadLayout defaultAndroid = GamepadLayout(
    id: '__default_android__',
    name: 'Android Gamepad',
    mode: GamepadMode.android,
    hapticFeedback: true,
    buttons: {
      'A': const ButtonConfig(label: 'A', colorValue: 0xFF2ECC71),
      'B': const ButtonConfig(label: 'B', colorValue: 0xFFE74C3C),
      'X': const ButtonConfig(label: 'X', colorValue: 0xFF3498DB),
      'Y': const ButtonConfig(label: 'Y', colorValue: 0xFFF39C12),
    },
  );

  static List<GamepadLayout> get builtIns => [
    defaultXInput,
    defaultDInput,
    defaultAndroid,
  ];

  bool get isBuiltIn => id.startsWith('__');

  // Serialisation ───────────────────────────────────────────────────────────

  factory GamepadLayout.fromJson(Map<String, dynamic> j) => GamepadLayout(
    id: j['id'] as String,
    name: j['name'] as String,
    mode: GamepadMode.values.firstWhere(
      (m) => m.name == j['mode'],
      orElse: () => GamepadMode.xinput,
    ),
    hapticFeedback: j['haptic'] as bool? ?? true,
    gyroEnabled: j['gyro'] as bool? ?? false,
    buttons: (j['buttons'] as Map<String, dynamic>? ?? {}).map(
      (k, v) => MapEntry(k, ButtonConfig.fromJson(v as Map<String, dynamic>)),
    ),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'mode': mode.name,
    'haptic': hapticFeedback,
    'gyro': gyroEnabled,
    'buttons': buttons.map((k, v) => MapEntry(k, v.toJson())),
  };

  GamepadLayout copyWith({
    String? name,
    GamepadMode? mode,
    bool? hapticFeedback,
    bool? gyroEnabled,
    Map<String, ButtonConfig>? buttons,
  }) => GamepadLayout(
    id: id,
    name: name ?? this.name,
    mode: mode ?? this.mode,
    hapticFeedback: hapticFeedback ?? this.hapticFeedback,
    gyroEnabled: gyroEnabled ?? this.gyroEnabled,
    buttons: buttons ?? this.buttons,
  );
}

// ── Preset manager ────────────────────────────────────────────────────────────

class GamepadPresetManager {
  static const _prefsKey = 'gamepad_presets_v1';
  static const _activeKey = 'gamepad_active_preset_id';

  List<GamepadLayout> _custom = [];
  String _activeId = GamepadLayout.defaultXInput.id;

  // Combined list: built-ins first, then custom
  List<GamepadLayout> get all => [...GamepadLayout.builtIns, ..._custom];

  GamepadLayout get active => all.firstWhere(
    (l) => l.id == _activeId,
    orElse: () => GamepadLayout.defaultXInput,
  );

  // Load ───────────────────────────────────────────────────────────────────

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _activeId = prefs.getString(_activeKey) ?? GamepadLayout.defaultXInput.id;
    final raw = prefs.getString(_prefsKey);
    if (raw != null) {
      final list = jsonDecode(raw) as List<dynamic>;
      _custom = list
          .map((e) => GamepadLayout.fromJson(e as Map<String, dynamic>))
          .toList();
    }
  }

  // Save ───────────────────────────────────────────────────────────────────

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _prefsKey,
      jsonEncode(_custom.map((l) => l.toJson()).toList()),
    );
    await prefs.setString(_activeKey, _activeId);
  }

  Future<void> setActive(GamepadLayout layout) async {
    _activeId = layout.id;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_activeKey, _activeId);
  }

  Future<void> save(GamepadLayout layout) async {
    final idx = _custom.indexWhere((l) => l.id == layout.id);
    if (idx >= 0) {
      _custom[idx] = layout;
    } else {
      _custom.add(layout);
    }
    await _persist();
  }

  Future<void> delete(GamepadLayout layout) async {
    _custom.removeWhere((l) => l.id == layout.id);
    if (_activeId == layout.id) {
      _activeId = GamepadLayout.defaultXInput.id;
    }
    await _persist();
  }
}

// ── Haptic helper ─────────────────────────────────────────────────────────────

Future<void> triggerHaptic({bool heavy = false}) async {
  try {
    if (heavy) {
      await HapticFeedback.heavyImpact();
    } else {
      await HapticFeedback.lightImpact();
    }
  } catch (_) {
    // Haptics not available on this device — silently ignore
  }
}
