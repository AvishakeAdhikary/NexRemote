import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart' as log;
import 'package:path_provider/path_provider.dart';

class Logger {
  static log.Logger? _logger;
  static bool _initialized = false;
  static const String _tag = 'NexRemote';

  /// Initialize the logger with file and console output
  static Future<void> init() async {
    if (_initialized) return;

    try {
      final outputs = <log.LogOutput>[log.ConsoleOutput()];

      // Production logging: app support directory (internal app storage)
      // Android: /data/data/com.neuralnexusstudios.nexremote/files
      // This is the standard location for app-internal files
      final supportDir = await getApplicationSupportDirectory();
      final appLogDir = Directory('${supportDir.path}/logs');

      if (!await appLogDir.exists()) {
        await appLogDir.create(recursive: true);
      }

      final appLogFile = File('${appLogDir.path}/nexremote.log');
      outputs.add(AdvancedFileOutput(
        path: appLogFile.path,
        maxFileSizeKB: 10 * 1024, // 10 MB
        maxBackupFileLength: 10,
      ));

      // Dev-only: also log to the project directory for easy access
      if (kDebugMode) {
        try {
          final projectLogDir = Directory('C:/Projects/NexRemote/logs');
          if (!await projectLogDir.exists()) {
            await projectLogDir.create(recursive: true);
          }

          final projectLogFile = File('${projectLogDir.path}/nexremote_dev.log');
          outputs.add(AdvancedFileOutput(
            path: projectLogFile.path,
            maxFileSizeKB: 10 * 1024, // 10 MB
            maxBackupFileLength: 10,
          ));
        } catch (e) {
          // Dev directory logging is optional — ignore on physical devices
        }
      }

      // Initialize logger with custom output
      _logger = log.Logger(
        filter: log.ProductionFilter(),
        printer: log.PrettyPrinter(
          methodCount: 0,
          errorMethodCount: 5,
          lineLength: 120,
          colors: true,
          printEmojis: false,
          dateTimeFormat: log.DateTimeFormat.onlyTimeAndSinceStart,
        ),
        output: log.MultiOutput(outputs),
      );

      _initialized = true;
      info('Logger initialized - logging to: ${appLogFile.path}');
    } catch (e) {
      // Fallback to console-only logger if file setup fails
      _logger = log.Logger(
        printer: log.SimplePrinter(printTime: true),
        output: log.ConsoleOutput(),
      );
      _initialized = true;
      error('Failed to initialize file logging, using console only', e);
    }
  }

  static void debug(String message) {
    if (_initialized && _logger != null) {
      _logger!.d('[$_tag] $message');
    }
  }

  static void info(String message) {
    if (_initialized && _logger != null) {
      _logger!.i('[$_tag] $message');
    }
  }

  static void warning(String message) {
    if (_initialized && _logger != null) {
      _logger!.w('[$_tag] $message');
    }
  }

  static void error(String message, [Object? error, StackTrace? stackTrace]) {
    if (_initialized && _logger != null) {
      _logger!.e('[$_tag] $message', error: error, stackTrace: stackTrace);
    }
  }

  /// Close logger and flush all outputs
  static Future<void> close() async {
    if (_logger != null) {
      await _logger!.close();
      _logger = null;
      _initialized = false;
    }
  }
}

/// Advanced file output with rotation support
class AdvancedFileOutput extends log.LogOutput {
  final String path;
  final int maxFileSizeKB;
  final int maxBackupFileLength;
  IOSink? _sink;
  File? _file;

  AdvancedFileOutput({
    required this.path,
    this.maxFileSizeKB = 10 * 1024, // 10 MB default
    this.maxBackupFileLength = 10,
  });

  @override
  Future<void> init() async {
    _file = File(path);
    _checkRotation();
    _sink = _file!.openWrite(mode: FileMode.append);
  }

  @override
  void output(log.OutputEvent event) {
    if (_sink == null) return;

    for (var line in event.lines) {
      final timestamp = DateTime.now();
      final formattedTime = '${timestamp.year}-${timestamp.month.toString().padLeft(2, '0')}-${timestamp.day.toString().padLeft(2, '0')} '
          '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}:${timestamp.second.toString().padLeft(2, '0')}';
      
      // Remove ANSI color codes for file output
      final cleanLine = line.replaceAll(RegExp(r'\\x1B\\[[0-9;]*m'), '');
      _sink!.writeln('$formattedTime | $cleanLine');
    }

    _checkRotation();
  }

  void _checkRotation() {
    if (_file == null || !_file!.existsSync()) return;

    final fileSizeKB = _file!.lengthSync() / 1024;
    if (fileSizeKB > maxFileSizeKB) {
      _rotateLog();
    }
  }

  void _rotateLog() {
    _sink?.close();

    // Rotate existing backup files
    for (int i = maxBackupFileLength - 1; i >= 1; i--) {
      final oldFile = File('$path.$i');
      final newFile = File('$path.${i + 1}');
      
      if (oldFile.existsSync()) {
        if (i == maxBackupFileLength - 1) {
          oldFile.deleteSync(); // Delete oldest file
        } else {
          oldFile.renameSync(newFile.path);
        }
      }
    }

    // Rename current file to .1
    if (_file!.existsSync()) {
      _file!.renameSync('$path.1');
    }

    // Create new file
    _file = File(path);
    _sink = _file!.openWrite(mode: FileMode.append);
  }

  @override
  Future<void> destroy() async {
    await _sink?.flush();
    await _sink?.close();
    _sink = null;
  }
}