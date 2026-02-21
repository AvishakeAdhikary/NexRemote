import 'dart:async';
import '../core/connection_manager.dart';

/// Sends keyboard events to the Windows server.
///
/// Key names must match what `pyautogui` / the server accepts:
/// single characters ('a', '1', '$'), or named keys from [Keys].
class KeyboardController {
  final ConnectionManager connectionManager;

  KeyboardController(this.connectionManager);

  /// Press a key, optionally with modifier keys held.
  ///
  /// If any modifiers are set the server receives a `hotkey` action;
  /// otherwise a plain `press` + delayed `release` pair.
  void sendKey(
    String key, {
    bool shift = false,
    bool ctrl = false,
    bool alt = false,
    bool win = false,
  }) {
    final modifiers = <String>[
      if (shift) 'shift',
      if (ctrl) 'ctrl',
      if (alt) 'alt',
      if (win) 'win',
    ];

    if (modifiers.isNotEmpty) {
      // Hotkey: hold modifiers + tap key, server releases all at once.
      connectionManager.sendMessage({
        'type': 'keyboard',
        'action': 'hotkey',
        'keys': [...modifiers, key],
      });
    } else {
      // Plain key: press then release after a short delay so the server
      // registers an actual down→up transition.
      connectionManager.sendMessage({
        'type': 'keyboard',
        'action': 'press',
        'key': key,
      });
      Future.delayed(const Duration(milliseconds: 50), () {
        connectionManager.sendMessage({
          'type': 'keyboard',
          'action': 'release',
          'key': key,
        });
      });
    }
  }

  /// Send a raw unicode string (e.g. from a virtual keyboard text field).
  void sendText(String text) {
    connectionManager.sendMessage({
      'type': 'keyboard',
      'action': 'type',
      'text': text,
    });
  }

  /// Send a multi-key hotkey chord such as `['ctrl', 'shift', 'esc']`.
  void sendHotkey(List<String> keys) {
    connectionManager.sendMessage({
      'type': 'keyboard',
      'action': 'hotkey',
      'keys': keys,
    });
  }

  /// Press and release a single named or special key (e.g. `Keys.enter`).
  void sendSpecialKey(String key) {
    connectionManager.sendMessage({
      'type': 'keyboard',
      'action': 'press',
      'key': key,
    });
    Future.delayed(const Duration(milliseconds: 50), () {
      connectionManager.sendMessage({
        'type': 'keyboard',
        'action': 'release',
        'key': key,
      });
    });
  }

  void dispose() {}
}

/// Well-known key name constants that match the server's expected values.
class Keys {
  Keys._();

  // ── Navigation ──────────────────────────────────────────────────────────
  static const String enter = 'enter';
  static const String backspace = 'backspace';
  static const String tab = 'tab';
  static const String space = 'space';
  static const String esc = 'esc';
  static const String delete = 'delete';
  static const String insert = 'insert';
  static const String home = 'home';
  static const String end = 'end';
  static const String pageUp = 'page_up';
  static const String pageDown = 'page_down';
  static const String arrowLeft = 'left';
  static const String arrowRight = 'right';
  static const String arrowUp = 'up';
  static const String arrowDown = 'down';

  // ── Function keys ───────────────────────────────────────────────────────
  static const String f1 = 'f1';
  static const String f2 = 'f2';
  static const String f3 = 'f3';
  static const String f4 = 'f4';
  static const String f5 = 'f5';
  static const String f6 = 'f6';
  static const String f7 = 'f7';
  static const String f8 = 'f8';
  static const String f9 = 'f9';
  static const String f10 = 'f10';
  static const String f11 = 'f11';
  static const String f12 = 'f12';

  // ── Modifiers ───────────────────────────────────────────────────────────
  static const String shift = 'shift';
  static const String ctrl = 'ctrl';
  static const String alt = 'alt';
  static const String win = 'win'; // Windows key
  static const String cmd = 'cmd'; // macOS alias

  // ── Common hotkeys (convenience) ────────────────────────────────────────
  static const List<String> copy = ['ctrl', 'c'];
  static const List<String> paste = ['ctrl', 'v'];
  static const List<String> cut = ['ctrl', 'x'];
  static const List<String> undo = ['ctrl', 'z'];
  static const List<String> redo = ['ctrl', 'y'];
  static const List<String> selectAll = ['ctrl', 'a'];
  static const List<String> taskManager = ['ctrl', 'shift', 'esc'];
  static const List<String> lockScreen = ['win', 'l'];
}
