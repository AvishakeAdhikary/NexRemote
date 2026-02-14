import '../core/connection_manager.dart';
import 'dart:async';
import 'package:flutter/foundation.dart';

class FileExplorerController {
  final ConnectionManager connectionManager;
  final StreamController<Map<String, dynamic>> _responseController =
      StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get responseStream => _responseController.stream;

  FileExplorerController(this.connectionManager);

  void requestDirectoryList(String path) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'list',
      'path': path,
    });
  }

  void openFile(String path) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'open',
      'path': path,
    });
  }

  void getFileProperties(String path) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'properties',
      'path': path,
    });
  }

  void searchFiles(String path, String query) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'search',
      'path': path,
      'query': query,
    });
  }

  void copyPath(String path) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'copy_path',
      'path': path,
    });
  }

  void handleResponse(Map<String, dynamic> data) {
    _responseController.add(data);
  }

  void dispose() {
    _responseController.close();
  }
}
