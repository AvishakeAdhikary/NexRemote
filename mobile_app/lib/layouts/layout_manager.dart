import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/logger.dart';
import 'default_layouts.dart';

class LayoutManager {
  static const String _layoutsKey = 'custom_layouts';
  static const String _activeLayoutKey = 'active_layout';
  
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
        final List<dynamic> layoutsList = jsonDecode(layoutsJson);
        _customLayouts = layoutsList
            .map((json) => GamepadLayout.fromJson(json))
            .toList();
      }
      
      // Load active layout
      final activeLayoutId = _prefs.getString(_activeLayoutKey);
      if (activeLayoutId != null) {
        _activeLayout = getLayout(activeLayoutId);
      }
      
      // If no active layout, use default
      if (_activeLayout == null) {
        _activeLayout = getDefaultLayout('standard_gamepad');
      }
      
      Logger.info('Loaded ${_customLayouts.length} custom layouts');
    } catch (e) {
      Logger.error('Failed to load layouts: $e');
    }
  }
  
  Future<void> _saveLayouts() async {
    try {
      final layoutsJson = jsonEncode(
        _customLayouts.map((layout) => layout.toJson()).toList()
      );
      await _prefs.setString(_layoutsKey, layoutsJson);
      Logger.info('Saved ${_customLayouts.length} custom layouts');
    } catch (e) {
      Logger.error('Failed to save layouts: $e');
    }
  }
  
  GamepadLayout? getLayout(String id) {
    // Check custom layouts
    for (var layout in _customLayouts) {
      if (layout.id == id) return layout;
    }
    
    // Check default layouts
    return getDefaultLayout(id);
  }
  
  GamepadLayout? getDefaultLayout(String id) {
    final defaults = DefaultLayouts.getDefaultLayouts();
    for (var defaultLayout in defaults) {
      if (defaultLayout['id'] == id) {
        return GamepadLayout.fromJson(jsonDecode(defaultLayout['data']));
      }
    }
    return null;
  }
  
  List<GamepadLayout> getAllLayouts() {
    final layouts = <GamepadLayout>[];
    
    // Add default layouts
    for (var defaultLayout in DefaultLayouts.getDefaultLayouts()) {
      layouts.add(GamepadLayout.fromJson(jsonDecode(defaultLayout['data'])));
    }
    
    // Add custom layouts
    layouts.addAll(_customLayouts);
    
    return layouts;
  }
  
  Future<void> saveLayout(GamepadLayout layout) async {
    // Check if layout already exists
    final index = _customLayouts.indexWhere((l) => l.id == layout.id);
    
    if (index >= 0) {
      _customLayouts[index] = layout;
    } else {
      _customLayouts.add(layout);
    }
    
    await _saveLayouts();
    Logger.info('Saved layout: ${layout.name}');
  }
  
  Future<void> deleteLayout(String id) async {
    _customLayouts.removeWhere((layout) => layout.id == id);
    await _saveLayouts();
    Logger.info('Deleted layout: $id');
  }
  
  Future<void> setActiveLayout(String id) async {
    _activeLayout = getLayout(id);
    await _prefs.setString(_activeLayoutKey, id);
    Logger.info('Active layout set to: $id');
  }
  
  GamepadLayout? get activeLayout => _activeLayout;
  
  String exportLayout(GamepadLayout layout) {
    return jsonEncode(layout.toJson());
  }
  
  GamepadLayout? importLayout(String jsonString) {
    try {
      final json = jsonDecode(jsonString);
      return GamepadLayout.fromJson(json);
    } catch (e) {
      Logger.error('Failed to import layout: $e');
      return null;
    }
  }
}

class GamepadLayout {
  final String id;
  final String name;
  final String version;
  final String orientation;
  final bool gyroEnabled;
  final bool accelEnabled;
  final List<LayoutElement> elements;
  
  GamepadLayout({
    required this.id,
    required this.name,
    required this.version,
    required this.orientation,
    this.gyroEnabled = false,
    this.accelEnabled = false,
    required this.elements,
  });
  
  factory GamepadLayout.fromJson(Map<String, dynamic> json) {
    return GamepadLayout(
      id: json['id'],
      name: json['name'],
      version: json['version'] ?? '1.0',
      orientation: json['orientation'] ?? 'landscape',
      gyroEnabled: json['gyro_enabled'] ?? false,
      accelEnabled: json['accel_enabled'] ?? false,
      elements: (json['elements'] as List)
          .map((e) => LayoutElement.fromJson(e))
          .toList(),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'version': version,
      'orientation': orientation,
      'gyro_enabled': gyroEnabled,
      'accel_enabled': accelEnabled,
      'elements': elements.map((e) => e.toJson()).toList(),
    };
  }
}

class LayoutElement {
  final String id;
  final String type;
  final Map<String, double> position;
  final dynamic size;
  final String? label;
  final String? action;
  final String? stick;
  final String? trigger;
  
  LayoutElement({
    required this.id,
    required this.type,
    required this.position,
    required this.size,
    this.label,
    this.action,
    this.stick,
    this.trigger,
  });
  
  factory LayoutElement.fromJson(Map<String, dynamic> json) {
    return LayoutElement(
      id: json['id'],
      type: json['type'],
      position: Map<String, double>.from(json['position']),
      size: json['size'],
      label: json['label'],
      action: json['action'],
      stick: json['stick'],
      trigger: json['trigger'],
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'position': position,
      'size': size,
      if (label != null) 'label': label,
      if (action != null) 'action': action,
      if (stick != null) 'stick': stick,
      if (trigger != null) 'trigger': trigger,
    };
  }
}