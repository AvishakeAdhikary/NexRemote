import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import 'dart:io';

class Config {
  static const String _deviceIdKey = 'device_id';
  static const String _deviceNameKey = 'device_name';
  static const String _lastServerKey = 'last_server';
  static const String _autoConnectKey = 'auto_connect';
  static const String _gyroSensitivityKey = 'gyro_sensitivity';
  static const String _useSecureConnectionKey = 'use_secure_connection';
  
  late SharedPreferences _prefs;
  
  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    
    // Generate device ID if not exists
    if (!_prefs.containsKey(_deviceIdKey)) {
      final uuid = const Uuid().v4();
      await _prefs.setString(_deviceIdKey, uuid);
    }
    
    // Set default device name if not exists
    if (!_prefs.containsKey(_deviceNameKey)) {
      final deviceName = Platform.isAndroid ? 'Android Device' : 'iOS Device';
      await _prefs.setString(_deviceNameKey, deviceName);
    }
  }
  
  String get deviceId => _prefs.getString(_deviceIdKey) ?? '';
  String get deviceName => _prefs.getString(_deviceNameKey) ?? 'Unknown';
  String? get lastServer => _prefs.getString(_lastServerKey);
  bool get autoConnect => _prefs.getBool(_autoConnectKey) ?? false;
  double get gyroSensitivity => _prefs.getDouble(_gyroSensitivityKey) ?? 1.0;
  bool get useSecureConnection => _prefs.getBool(_useSecureConnectionKey) ?? false;
  
  Future<void> setDeviceName(String name) async {
    await _prefs.setString(_deviceNameKey, name);
  }
  
  Future<void> setLastServer(String server) async {
    await _prefs.setString(_lastServerKey, server);
  }
  
  Future<void> setAutoConnect(bool value) async {
    await _prefs.setBool(_autoConnectKey, value);
  }
  
  Future<void> setGyroSensitivity(double value) async {
    await _prefs.setDouble(_gyroSensitivityKey, value);
  }
  
  Future<void> setUseSecureConnection(bool value) async {
    await _prefs.setBool(_useSecureConnectionKey, value);
  }
}