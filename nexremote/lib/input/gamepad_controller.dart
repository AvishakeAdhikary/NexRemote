import 'dart:async';
import 'package:flutter/services.dart';
import '../core/connection_manager.dart';
import 'gamepad_preset.dart';

export 'gamepad_preset.dart';

/// Sends gamepad input to the server, mode-aware, with optional haptic feedback.
class GamepadController {
  final ConnectionManager connectionManager;
  final GamepadPresetManager presetManager = GamepadPresetManager();

  GamepadLayout _layout = GamepadLayout.defaultXInput;
  bool _presetsLoaded = false;

  GamepadController(this.connectionManager);

  // ── Preset / layout management ─────────────────────────────────────────

  GamepadLayout get activeLayout => _layout;
  GamepadMode get mode => _layout.mode;
  bool get hapticEnabled => _layout.hapticFeedback;

  Future<void> loadPresets() async {
    if (_presetsLoaded) return;
    await presetManager.load();
    _layout = presetManager.active;
    _presetsLoaded = true;

    // Notify server of the current mode immediately after loading
    _sendModeChange(_layout.mode);
  }

  Future<void> applyLayout(GamepadLayout layout) async {
    final modeChanged = layout.mode != _layout.mode;
    _layout = layout;
    await presetManager.setActive(layout);
    if (modeChanged) {
      _sendModeChange(layout.mode);
    }
  }

  Future<void> saveCustomLayout(GamepadLayout layout) async {
    await presetManager.save(layout);
  }

  Future<void> deleteCustomLayout(GamepadLayout layout) async {
    await presetManager.delete(layout);
    // Fall back to default if we just deleted the active one
    if (_layout.id == layout.id) {
      await applyLayout(GamepadLayout.defaultXInput);
    }
  }

  // ── Mode switch ────────────────────────────────────────────────────────

  void _sendModeChange(GamepadMode m) {
    if (m == GamepadMode.android) return; // Android mode is client-side only
    connectionManager.sendMessage({'type': 'gamepad_mode', 'mode': m.name});
  }

  // ── Message type for current mode ──────────────────────────────────────

  String get _msgType {
    switch (_layout.mode) {
      case GamepadMode.xinput:
        return 'gamepad';
      case GamepadMode.dinput:
        return 'gamepad_dinput';
      case GamepadMode.android:
        return 'gamepad_android';
    }
  }

  // ── Input senders ──────────────────────────────────────────────────────

  void sendButton(String button, bool pressed) {
    if (pressed && _layout.hapticFeedback) {
      HapticFeedback.lightImpact();
    }
    connectionManager.sendMessage({
      'type': _msgType,
      'input_type': 'button',
      'button': button,
      'pressed': pressed,
    });
  }

  void sendDPad(String direction, bool pressed) {
    if (pressed && _layout.hapticFeedback) {
      HapticFeedback.lightImpact();
    }
    connectionManager.sendMessage({
      'type': _msgType,
      'input_type': 'dpad',
      'direction': direction.toLowerCase(),
      'pressed': pressed,
    });
  }

  void sendJoystick(String stick, double x, double y) {
    connectionManager.sendMessage({
      'type': _msgType,
      'input_type': 'joystick',
      'stick': stick,
      'x': x,
      'y': y,
    });
  }

  void sendTrigger(String trigger, double value) {
    connectionManager.sendMessage({
      'type': _msgType,
      'input_type': 'trigger',
      'trigger': trigger,
      'value': value,
    });
  }

  void sendGyroData(double x, double y, double z) {
    connectionManager.sendMessage({
      'type': _msgType,
      'input_type': 'gyro',
      'x': x,
      'y': y,
      'z': z,
    });
  }

  void dispose() {
    // Nothing persistent to clean up
  }
}
