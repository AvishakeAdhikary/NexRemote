import '../core/connection_manager.dart';

class MediaController {
  final ConnectionManager connectionManager;

  MediaController(this.connectionManager);

  void play() {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'play',
    });
  }

  void pause() {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'pause',
    });
  }

  void stop() {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'stop',
    });
  }

  void next() {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'next',
    });
  }

  void previous() {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'previous',
    });
  }

  void setVolume(int volume) {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'volume',
      'value': volume,
    });
  }

  void toggleMute() {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'mute_toggle',
    });
  }

  void seek(double position) {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'seek',
      'position': position,
    });
  }

  void requestMediaInfo() {
    connectionManager.sendMessage({
      'type': 'media_control',
      'action': 'get_info',
    });
  }

  void dispose() {
    // Cleanup if needed
  }
}
