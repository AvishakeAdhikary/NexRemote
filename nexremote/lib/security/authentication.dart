import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/logger.dart';

class DeviceAuthenticator {
  late SharedPreferences _prefs;
  static const String _authTokenKey = 'auth_token';
  static const String _deviceSecretKey = 'device_secret';
  
  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    
    // Generate device secret if not exists
    if (!_prefs.containsKey(_deviceSecretKey)) {
      final secret = _generateSecret();
      await _prefs.setString(_deviceSecretKey, secret);
    }
  }
  
  String _generateSecret() {
    final timestamp = DateTime.now().millisecondsSinceEpoch.toString();
    final random = DateTime.now().microsecondsSinceEpoch.toString();
    final bytes = utf8.encode('$timestamp-$random');
    final digest = sha256.convert(bytes);
    return digest.toString();
  }
  
  /// Generate authentication token
  String generateAuthToken(String deviceId, String deviceName) {
    final secret = _prefs.getString(_deviceSecretKey) ?? _generateSecret();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    
    final payload = '$deviceId:$deviceName:$timestamp:$secret';
    final bytes = utf8.encode(payload);
    final digest = sha256.convert(bytes);
    
    return digest.toString();
  }
  
  /// Verify authentication response
  bool verifyAuthResponse(Map<String, dynamic> response) {
    try {
      if (response['type'] == 'auth_success') {
        // Store auth token
        final token = response['token'] as String?;
        if (token != null) {
          _prefs.setString(_authTokenKey, token);
        }
        return true;
      }
      return false;
    } catch (e) {
      Logger.error('Auth verification error: $e');
      return false;
    }
  }
  
  /// Get stored authentication token
  String? getAuthToken() {
    return _prefs.getString(_authTokenKey);
  }
  
  /// Clear authentication
  Future<void> clearAuth() async {
    await _prefs.remove(_authTokenKey);
    Logger.info('Authentication cleared');
  }
  
  /// Check if authenticated
  bool isAuthenticated() {
    return _prefs.containsKey(_authTokenKey);
  }
}