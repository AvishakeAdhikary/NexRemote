import '../core/connection_manager.dart';
import 'dart:async';

class TaskManagerController {
  final ConnectionManager connectionManager;
  final StreamController<Map<String, dynamic>> _responseController =
      StreamController<Map<String, dynamic>>.broadcast();
  StreamSubscription? _messageSubscription;

  Stream<Map<String, dynamic>> get responseStream => _responseController.stream;

  TaskManagerController(this.connectionManager) {
    // Route task_manager messages from the global message stream
    _messageSubscription = connectionManager.messageStream.listen((data) {
      if (data['type'] == 'task_manager') {
        _responseController.add(data);
      }
    });
  }

  void requestProcessList() {
    connectionManager.sendMessage({
      'type': 'task_manager',
      'action': 'list_processes',
    });
  }

  void endProcess(int pid) {
    connectionManager.sendMessage({
      'type': 'task_manager',
      'action': 'end_process',
      'pid': pid,
    });
  }

  void requestSystemInfo() {
    connectionManager.sendMessage({
      'type': 'task_manager',
      'action': 'system_info',
    });
  }

  void handleResponse(Map<String, dynamic> data) {
    _responseController.add(data);
  }

  void dispose() {
    _messageSubscription?.cancel();
    _responseController.close();
  }
}
