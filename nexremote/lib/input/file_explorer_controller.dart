import '../core/connection_manager.dart';
import 'dart:async';
import 'package:flutter/foundation.dart';

class FileExplorerController {
  final ConnectionManager connectionManager;
  final StreamController<Map<String, dynamic>> _responseController =
      StreamController<Map<String, dynamic>>.broadcast();
  StreamSubscription? _messageSubscription;

  Stream<Map<String, dynamic>> get responseStream => _responseController.stream;

  FileExplorerController(this.connectionManager) {
    // Route file_explorer messages from the global message stream
    _messageSubscription = connectionManager.messageStream.listen((data) {
      if (data['type'] == 'file_explorer') {
        _responseController.add(data);
      }
    });
  }

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

  // CRUD Operations

  void createFolder(String parentPath, String name) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'create_folder',
      'path': parentPath,
      'name': name,
    });
  }

  void createFile(String parentPath, String name, {String content = ''}) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'create_file',
      'path': parentPath,
      'name': name,
      'content': content,
    });
  }

  void renameItem(String path, String newName) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'rename',
      'path': path,
      'new_name': newName,
    });
  }

  void deleteItem(String path) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'delete',
      'path': path,
    });
  }

  void readFile(String path) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'read_file',
      'path': path,
    });
  }

  void writeFile(String path, String content) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'write_file',
      'path': path,
      'content': content,
    });
  }

  void copyItem(String source, String destination) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'copy',
      'source': source,
      'destination': destination,
    });
  }

  void moveItem(String source, String destination) {
    connectionManager.sendMessage({
      'type': 'file_explorer',
      'action': 'move',
      'source': source,
      'destination': destination,
    });
  }

  void dispose() {
    _messageSubscription?.cancel();
    _responseController.close();
  }
}
