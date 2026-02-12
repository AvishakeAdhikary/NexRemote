import '../core/connection_manager.dart';

class KeyboardController {
  final ConnectionManager connectionManager;
  
  KeyboardController(this.connectionManager);
  
  void sendKey(String key, {bool shift = false, bool ctrl = false, bool alt = false}) {
    final modifiers = <String>[];
    if (shift) modifiers.add('shift');
    if (ctrl) modifiers.add('ctrl');
    if (alt) modifiers.add('alt');
    
    connectionManager.sendMessage({
      'type': 'keyboard',
      'action': modifiers.isNotEmpty ? 'hotkey' : 'press',
      'key': key,
      'keys': modifiers.isNotEmpty ? [...modifiers, key] : null,
    });
    
    // Send release after a short delay
    Future.delayed(const Duration(milliseconds': 50), () {
      connectionManager.sendMessage({
        'type': 'keyboard',
        'action': 'release',
        'key': key,
      });
    });
  }
  
  void sendText(String text) {
    connectionManager.sendMessage({
      'type': 'keyboard',
      'action': 'type',
      'text': text,
    });
  }
  
  void sendHotkey(List<String> keys) {
    connectionManager.sendMessage({
      'type': 'keyboard',
      'action': 'hotkey',
      'keys': keys,
    });
  }
  
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
  
  void dispose() {
    // Cleanup if needed
  }
}

// Common key constants
class Keys {
  static const String enter = 'enter';
  static const String backspace = 'backspace';
  static const String tab = 'tab';
  static const String space = 'space';
  static const String esc = 'esc';
  static const String delete = 'delete';
  static const String home = 'home';
  static const String end = 'end';
  static const String pageUp = 'page_up';
  static const String pageDown = 'page_down';
  static const String arrowLeft = 'left';
  static const String arrowRight = 'right';
  static const String arrowUp = 'up';
  static const String arrowDown = 'down';
  
  // Function keys
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
  
  // Modifiers
  static const String shift = 'shift';
  static const String ctrl = 'ctrl';
  static const String alt = 'alt';
  static const String cmd = 'cmd';
}