/// Protocol definitions for NexRemote communication
/// Message types and structures

class Protocol {
  // Message Types
  static const String authRequest = 'auth';
  static const String authSuccess = 'auth_success';
  static const String authFailed = 'auth_failed';
  static const String connectionRejected = 'connection_rejected';
  
  static const String keyboard = 'keyboard';
  static const String mouse = 'mouse';
  static const String gamepad = 'gamepad';
  static const String sensor = 'sensor';
  
  static const String screenFrame = 'screen_frame';
  static const String cameraFrame = 'camera_frame';
  static const String requestScreen = 'request_screen';
  
  static const String clipboard = 'clipboard';
  static const String fileTransfer = 'file_transfer';
  
  // Keyboard Actions
  static const String keyboardType = 'type';
  static const String keyboardPress = 'press';
  static const String keyboardRelease = 'release';
  static const String keyboardHotkey = 'hotkey';
  
  // Mouse Actions
  static const String mouseMove = 'move';
  static const String mouseMoveRelative = 'move_relative';
  static const String mouseClick = 'click';
  static const String mousePress = 'press';
  static const String mouseRelease = 'release';
  static const String mouseScroll = 'scroll';
  
  // Gamepad Input Types
  static const String gamepadButton = 'button';
  static const String gamepadTrigger = 'trigger';
  static const String gamepadJoystick = 'joystick';
  static const String gamepadDpad = 'dpad';
  static const String gamepadGyro = 'gyro';
  
  // Sensor Types
  static const String sensorGyroscope = 'gyroscope';
  static const String sensorAccelerometer = 'accelerometer';
  
  /// Create authentication message
  static Map<String, dynamic> createAuthMessage({
    required String deviceId,
    required String deviceName,
    String version = '1.0.0',
  }) {
    return {
      'type': authRequest,
      'device_id': deviceId,
      'device_name': deviceName,
      'version': version,
    };
  }
  
  /// Create keyboard message
  static Map<String, dynamic> createKeyboardMessage({
    required String action,
    String? key,
    String? text,
    List<String>? keys,
  }) {
    return {
      'type': keyboard,
      'action': action,
      if (key != null) 'key': key,
      if (text != null) 'text': text,
      if (keys != null) 'keys': keys,
    };
  }
  
  /// Create mouse message
  static Map<String, dynamic> createMouseMessage({
    required String action,
    int? x,
    int? y,
    int? dx,
    int? dy,
    String? button,
    int? count,
  }) {
    return {
      'type': mouse,
      'action': action,
      if (x != null) 'x': x,
      if (y != null) 'y': y,
      if (dx != null) 'dx': dx,
      if (dy != null) 'dy': dy,
      if (button != null) 'button': button,
      if (count != null) 'count': count,
    };
  }
  
  /// Create gamepad message
  static Map<String, dynamic> createGamepadMessage({
    required String inputType,
    String? button,
    bool? pressed,
    String? trigger,
    double? value,
    String? stick,
    double? x,
    double? y,
    String? direction,
  }) {
    return {
      'type': gamepad,
      'input_type': inputType,
      if (button != null) 'button': button,
      if (pressed != null) 'pressed': pressed,
      if (trigger != null) 'trigger': trigger,
      if (value != null) 'value': value,
      if (stick != null) 'stick': stick,
      if (x != null) 'x': x,
      if (y != null) 'y': y,
      if (direction != null) 'direction': direction,
    };
  }
  
  /// Create sensor message
  static Map<String, dynamic> createSensorMessage({
    required String sensorType,
    required double x,
    required double y,
    required double z,
  }) {
    return {
      'type': sensor,
      'sensor_type': sensorType,
      'x': x,
      'y': y,
      'z': z,
    };
  }
  
  /// Parse incoming message
  static MessageType getMessageType(Map<String, dynamic> message) {
    final type = message['type'] as String?;
    
    switch (type) {
      case authSuccess:
        return MessageType.authSuccess;
      case authFailed:
        return MessageType.authFailed;
      case connectionRejected:
        return MessageType.connectionRejected;
      case screenFrame:
        return MessageType.screenFrame;
      case clipboard:
        return MessageType.clipboard;
      default:
        return MessageType.unknown;
    }
  }
}

enum MessageType {
  authSuccess,
  authFailed,
  connectionRejected,
  screenFrame,
  clipboard,
  unknown,
}