import 'dart:developer' as developer;

class Logger {
  static bool _initialized = false;
  static String _tag = 'NexRemote';

  static void init() {
    _initialized = true;
  }

  static void debug(String message) {
    if (_initialized) {
      developer.log(message, name: _tag, level: 500);
    }
  }

  static void info(String message) {
    if (_initialized) {
      developer.log(message, name: _tag, level: 800);
    }
  }

  static void warning(String message) {
    if (_initialized) {
      developer.log(message, name: _tag, level: 900);
    }
  }

  static void error(String message, [Object? error, StackTrace? stackTrace]) {
    if (_initialized) {
      developer.log(
        message,
        name: _tag,
        level: 1000,
        error: error,
        stackTrace: stackTrace,
      );
    }
  }
}