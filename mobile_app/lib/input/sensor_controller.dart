import 'dart:async';
import 'package:sensors_plus/sensors_plus.dart';
import '../core/connection_manager.dart';
import '../utils/logger.dart';

class SensorController {
  final ConnectionManager connectionManager;
  
  StreamSubscription? _gyroSubscription;
  StreamSubscription? _accelSubscription;
  
  double _gyroSensitivity = 1.0;
  double _accelSensitivity = 1.0;
  
  bool _gyroEnabled = false;
  bool _accelEnabled = false;
  
  SensorController(this.connectionManager);
  
  void setGyroSensitivity(double sensitivity) {
    _gyroSensitivity = sensitivity;
  }
  
  void setAccelSensitivity(double sensitivity) {
    _accelSensitivity = sensitivity;
  }
  
  void startGyroscope() {
    if (_gyroEnabled) return;
    
    _gyroEnabled = true;
    _gyroSubscription = gyroscopeEvents.listen((GyroscopeEvent event) {
      connectionManager.sendMessage({
        'type': 'sensor',
        'sensor_type': 'gyroscope',
        'x': event.x * _gyroSensitivity,
        'y': event.y * _gyroSensitivity,
        'z': event.z * _gyroSensitivity,
      });
    });
    
    Logger.info('Gyroscope started');
  }
  
  void stopGyroscope() {
    _gyroEnabled = false;
    _gyroSubscription?.cancel();
    _gyroSubscription = null;
    Logger.info('Gyroscope stopped');
  }
  
  void startAccelerometer() {
    if (_accelEnabled) return;
    
    _accelEnabled = true;
    _accelSubscription = accelerometerEvents.listen((AccelerometerEvent event) {
      connectionManager.sendMessage({
        'type': 'sensor',
        'sensor_type': 'accelerometer',
        'x': event.x * _accelSensitivity,
        'y': event.y * _accelSensitivity,
        'z': event.z * _accelSensitivity,
      });
    });
    
    Logger.info('Accelerometer started');
  }
  
  void stopAccelerometer() {
    _accelEnabled = false;
    _accelSubscription?.cancel();
    _accelSubscription = null;
    Logger.info('Accelerometer stopped');
  }
  
  bool get isGyroEnabled => _gyroEnabled;
  bool get isAccelEnabled => _accelEnabled;
  
  void dispose() {
    stopGyroscope();
    stopAccelerometer();
  }
}

class SensorData {
  final double x;
  final double y;
  final double z;
  final DateTime timestamp;
  
  SensorData({
    required this.x,
    required this.y,
    required this.z,
    required this.timestamp,
  });
}