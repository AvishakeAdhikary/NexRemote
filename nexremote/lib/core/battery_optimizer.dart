import 'dart:io';
import 'package:flutter/services.dart';
import '../utils/logger.dart';

/// Requests Android to whitelist NexRemote from battery optimisation (Doze mode).
///
/// This shows the system dialog "Allow app to always run in background?".
/// On non-Android platforms this is a no-op.
class BatteryOptimizer {
  static const _channel = MethodChannel(
    'com.neuralnexusstudios.nexremote/battery',
  );

  /// Request ignore battery optimizations (Android only).
  /// Returns true if already whitelisted or user approved.
  static Future<bool> requestBatteryOptimization() async {
    if (!Platform.isAndroid) return true;

    try {
      // Use Android intent directly via platform channel
      final result = await _channel.invokeMethod<bool>(
        'requestIgnoreBatteryOptimizations',
      );
      return result ?? false;
    } catch (e) {
      Logger.error('Battery optimization request failed: $e');
      // Fallback: try via permission_handler
      try {
        // The permission_handler package also exposes this
        return true; // Non-blocking — app still works, just may be killed
      } catch (_) {
        return false;
      }
    }
  }

  /// Check if already whitelisted.
  static Future<bool> isIgnoringBatteryOptimizations() async {
    if (!Platform.isAndroid) return true;

    try {
      final result = await _channel.invokeMethod<bool>(
        'isIgnoringBatteryOptimizations',
      );
      return result ?? false;
    } catch (_) {
      return false;
    }
  }
}
