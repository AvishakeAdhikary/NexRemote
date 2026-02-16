import '../core/connection_manager.dart';

class GamepadController {
  final ConnectionManager connectionManager;

  GamepadController(this.connectionManager);

  void sendButton(String button, bool pressed) {
    connectionManager.sendMessage({
      'type': 'gamepad',
      'input_type': 'button',
      'button': button,
      'pressed': pressed,
    });
  }

  void sendDPad(String direction, bool pressed) {
    connectionManager.sendMessage({
      'type': 'gamepad',
      'input_type': 'dpad',
      'direction': direction.toLowerCase(),
      'pressed': pressed,
    });
  }

  void sendJoystick(String stick, double x, double y) {
    connectionManager.sendMessage({
      'type': 'gamepad',
      'input_type': 'joystick',
      'stick': stick,
      'x': x,
      'y': y,
    });
  }

  void sendTrigger(String trigger, double value) {
    connectionManager.sendMessage({
      'type': 'gamepad',
      'input_type': 'trigger',
      'trigger': trigger,
      'value': value,
    });
  }

  void sendGyroData(double x, double y, double z) {
    connectionManager.sendMessage({
      'type': 'gamepad',
      'input_type': 'gyro',
      'x': x,
      'y': y,
      'z': z,
    });
  }

  void dispose() {
    // Cleanup if needed
  }
}