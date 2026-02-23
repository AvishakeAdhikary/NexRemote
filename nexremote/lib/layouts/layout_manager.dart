import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/logger.dart';
import 'default_layouts.dart';

// ── Macro ─────────────────────────────────────────────────────────────────────

/// A single step inside a button macro.
class MacroStep {
  final String action; // e.g. 'button:A', 'dpad:UP', 'keyboard:r'
  final int delayMs; // wait BEFORE triggering this step

  const MacroStep({required this.action, this.delayMs = 0});

  factory MacroStep.fromJson(Map<String, dynamic> j) => MacroStep(
    action: j['action'] as String,
    delayMs: (j['delay'] as int?) ?? 0,
  );

  Map<String, dynamic> toJson() => {'action': action, 'delay': delayMs};
}

// ── Layout element ────────────────────────────────────────────────────────────

class LayoutElement {
  final String id;
  final String
  type; // 'button', 'joystick', 'dpad', 'face_buttons', 'trigger', 'macro'
  final double x; // fractional 0-1 of canvas width
  final double y; // fractional 0-1 of canvas height
  final double width; // logical px
  final double height; // logical px
  final double scale; // multiplier applied on top of width/height
  final int colorValue; // ARGB
  final String? label;
  final String? action; // canonical button / keyboard / mouse action
  final String? stick; // 'left' or 'right' for joystick type
  final String? trigger; // 'LT' or 'RT' for trigger type
  final List<MacroStep> macro; // non-empty ⇒ this is a macro button

  const LayoutElement({
    required this.id,
    required this.type,
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    this.scale = 1.0,
    this.colorValue = 0xFF374151,
    this.label,
    this.action,
    this.stick,
    this.trigger,
    this.macro = const [],
  });

  // ── Serialisation ──────────────────────────────────────────────────────────

  factory LayoutElement.fromJson(Map<String, dynamic> j) {
    // Support old format with position map and size int/map
    double px, py;
    if (j.containsKey('position')) {
      final pos = j['position'] as Map<String, dynamic>;
      px = (pos['x'] as num).toDouble();
      py = (pos['y'] as num).toDouble();
    } else {
      px = (j['x'] as num? ?? 0).toDouble();
      py = (j['y'] as num? ?? 0).toDouble();
    }

    double w, h;
    final sz = j['size'];
    if (sz is Map) {
      w = (sz['width'] as num? ?? 60).toDouble();
      h = (sz['height'] as num? ?? 40).toDouble();
    } else if (sz is num) {
      w = sz.toDouble();
      h = sz.toDouble();
    } else {
      w = (j['width'] as num? ?? 60).toDouble();
      h = (j['height'] as num? ?? 60).toDouble();
    }

    return LayoutElement(
      id: j['id'] as String,
      type: j['type'] as String,
      x: px,
      y: py,
      width: w,
      height: h,
      scale: (j['scale'] as num? ?? 1.0).toDouble(),
      colorValue: (j['color'] as int?) ?? 0xFF374151,
      label: j['label'] as String?,
      action: j['action'] as String?,
      stick: j['stick'] as String?,
      trigger: j['trigger'] as String?,
      macro:
          (j['macro'] as List<dynamic>?)
              ?.map((s) => MacroStep.fromJson(s as Map<String, dynamic>))
              .toList() ??
          const [],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type,
    'x': x,
    'y': y,
    'width': width,
    'height': height,
    'scale': scale,
    'color': colorValue,
    if (label != null) 'label': label,
    if (action != null) 'action': action,
    if (stick != null) 'stick': stick,
    if (trigger != null) 'trigger': trigger,
    if (macro.isNotEmpty) 'macro': macro.map((s) => s.toJson()).toList(),
  };

  // ── copyWith ───────────────────────────────────────────────────────────────

  LayoutElement copyWith({
    String? id,
    String? type,
    double? x,
    double? y,
    double? width,
    double? height,
    double? scale,
    int? colorValue,
    Object? label = _sentinel,
    Object? action = _sentinel,
    Object? stick = _sentinel,
    Object? trigger = _sentinel,
    List<MacroStep>? macro,
  }) => LayoutElement(
    id: id ?? this.id,
    type: type ?? this.type,
    x: x ?? this.x,
    y: y ?? this.y,
    width: width ?? this.width,
    height: height ?? this.height,
    scale: scale ?? this.scale,
    colorValue: colorValue ?? this.colorValue,
    label: label == _sentinel ? this.label : label as String?,
    action: action == _sentinel ? this.action : action as String?,
    stick: stick == _sentinel ? this.stick : stick as String?,
    trigger: trigger == _sentinel ? this.trigger : trigger as String?,
    macro: macro ?? this.macro,
  );

  // Effective pixel size (scale applied)
  double get effectiveWidth => width * scale;
  double get effectiveHeight => height * scale;
}

// sentinel object for copyWith nullable-passthrough
const _sentinel = Object();

// ── Full layout ───────────────────────────────────────────────────────────────

class GamepadLayout {
  final String id;
  final String name;
  final String version;
  final String orientation; // 'landscape' | 'portrait'
  final bool gyroEnabled;
  final bool accelEnabled;
  final bool hapticFeedback;
  final String mode; // 'xinput' | 'dinput' | 'android'
  final List<LayoutElement> elements;

  const GamepadLayout({
    required this.id,
    required this.name,
    this.version = '2.0',
    this.orientation = 'landscape',
    this.gyroEnabled = false,
    this.accelEnabled = false,
    this.hapticFeedback = true,
    this.mode = 'xinput',
    required this.elements,
  });

  // ── Serialisation ──────────────────────────────────────────────────────────

  factory GamepadLayout.fromJson(Map<String, dynamic> j) => GamepadLayout(
    id: j['id'] as String,
    name: j['name'] as String,
    version: j['version'] as String? ?? '1.0',
    orientation: j['orientation'] as String? ?? 'landscape',
    gyroEnabled: j['gyro_enabled'] as bool? ?? false,
    accelEnabled: j['accel_enabled'] as bool? ?? false,
    hapticFeedback: j['haptic'] as bool? ?? true,
    mode: j['mode'] as String? ?? 'xinput',
    elements: (j['elements'] as List<dynamic>)
        .map((e) => LayoutElement.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'version': version,
    'orientation': orientation,
    'gyro_enabled': gyroEnabled,
    'accel_enabled': accelEnabled,
    'haptic': hapticFeedback,
    'mode': mode,
    'elements': elements.map((e) => e.toJson()).toList(),
  };

  // ── copyWith ───────────────────────────────────────────────────────────────

  GamepadLayout copyWith({
    String? id,
    String? name,
    String? version,
    String? orientation,
    bool? gyroEnabled,
    bool? accelEnabled,
    bool? hapticFeedback,
    String? mode,
    List<LayoutElement>? elements,
  }) => GamepadLayout(
    id: id ?? this.id,
    name: name ?? this.name,
    version: version ?? this.version,
    orientation: orientation ?? this.orientation,
    gyroEnabled: gyroEnabled ?? this.gyroEnabled,
    accelEnabled: accelEnabled ?? this.accelEnabled,
    hapticFeedback: hapticFeedback ?? this.hapticFeedback,
    mode: mode ?? this.mode,
    elements: elements ?? this.elements,
  );
}

// ── Layout manager ────────────────────────────────────────────────────────────

class LayoutManager {
  static const String _layoutsKey = 'custom_layouts_v2';
  static const String _activeLayoutKey = 'active_layout_v2';

  late SharedPreferences _prefs;
  List<GamepadLayout> _customLayouts = [];
  GamepadLayout? _activeLayout;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    await _loadLayouts();
  }

  Future<void> _loadLayouts() async {
    try {
      final layoutsJson = _prefs.getString(_layoutsKey);
      if (layoutsJson != null) {
        final list = jsonDecode(layoutsJson) as List<dynamic>;
        _customLayouts = list
            .map((e) => GamepadLayout.fromJson(e as Map<String, dynamic>))
            .toList();
      }

      final activeId = _prefs.getString(_activeLayoutKey);
      if (activeId != null) {
        _activeLayout = getLayout(activeId);
      }
      _activeLayout ??= getDefaultLayout('standard_gamepad');

      Logger.info('Loaded ${_customLayouts.length} custom layouts');
    } catch (e) {
      Logger.error('Failed to load layouts: $e');
      _activeLayout = getDefaultLayout('standard_gamepad');
    }
  }

  Future<void> _saveLayouts() async {
    final json = jsonEncode(_customLayouts.map((l) => l.toJson()).toList());
    await _prefs.setString(_layoutsKey, json);
  }

  // ── CRUD ──────────────────────────────────────────────────────────────────

  GamepadLayout? getLayout(String id) {
    for (final l in _customLayouts) {
      if (l.id == id) return l;
    }
    return getDefaultLayout(id);
  }

  GamepadLayout? getDefaultLayout(String id) {
    for (final d in DefaultLayouts.getDefaultLayouts()) {
      if (d['id'] == id) {
        return GamepadLayout.fromJson(
          jsonDecode(d['data'] as String) as Map<String, dynamic>,
        );
      }
    }
    return null;
  }

  List<GamepadLayout> getAllLayouts() {
    // Custom layouts take precedence — hide any default whose ID was overridden.
    final customIds = _customLayouts.map((l) => l.id).toSet();
    final defaults = DefaultLayouts.getDefaultLayouts()
        .where((d) => !customIds.contains(d['id']))
        .map(
          (d) => GamepadLayout.fromJson(
            jsonDecode(d['data'] as String) as Map<String, dynamic>,
          ),
        )
        .toList();
    return [...defaults, ..._customLayouts];
  }

  Future<void> saveLayout(GamepadLayout layout) async {
    final idx = _customLayouts.indexWhere((l) => l.id == layout.id);
    if (idx >= 0) {
      _customLayouts[idx] = layout;
    } else {
      _customLayouts.add(layout);
    }
    await _saveLayouts();
  }

  Future<void> deleteLayout(String id) async {
    _customLayouts.removeWhere((l) => l.id == id);
    if (_activeLayout?.id == id) {
      _activeLayout = getDefaultLayout('standard_gamepad');
    }
    await _saveLayouts();
  }

  Future<void> setActiveLayout(GamepadLayout layout) async {
    _activeLayout = layout;
    await _prefs.setString(_activeLayoutKey, layout.id);
  }

  GamepadLayout? get activeLayout => _activeLayout;

  String exportLayout(GamepadLayout layout) => jsonEncode(layout.toJson());

  GamepadLayout? importLayout(String jsonString) {
    try {
      return GamepadLayout.fromJson(
        jsonDecode(jsonString) as Map<String, dynamic>,
      );
    } catch (e) {
      Logger.error('Failed to import layout: $e');
      return null;
    }
  }
}
