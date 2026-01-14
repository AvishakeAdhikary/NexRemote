import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:nexremote/services/network_service.dart';

class FileBrowserScreen extends StatefulWidget {
  const FileBrowserScreen({Key? key}) : super(key: key);

  @override
  State<FileBrowserScreen> createState() => _FileBrowserScreenState();
}

class _FileBrowserScreenState extends State<FileBrowserScreen> {
  List<Map<String, dynamic>> _files = [];
  String _currentPath = '';
  bool _loading = false;

  @override
  void initState(){
    super.initState();
    _loadFiles('');
  }

  void _loadFiles(String path){
    setState(() => _loading = true);
    final network = Provider.of<NetworkService>(context, listen: false);
    network.sendCommand('file_list', {'path': path});

    // Listen for response
    network.messageStream.listen((message) {
      if (message['type'] == 'file_list_response') {
        setState(() {
          _files = List<Map<String, dynamic>>.from(message['data']['files'] ?? []);
          _currentPath = path;
          _loading = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_currentPath.isEmpty ? 'PC Files' : _currentPath),
      ),
      body: _loading
        ? const Center(child: CircularProgressIndicator())
        : ListView.builder(
          itemCount: _files.length,
          itemBuilder: (context, index) {
            final file = _files[index];
            final isFolder = file['type'] == 'folder' || file['type'] == 'drive';

            return ListTile(
              leading: Icon(
                isFolder ? Icons.folder : Icons.insert_drive_file,
                color: isFolder ? Colors.amber : Colors.blue,
              ),
              title: Text(file['name']),
              subtitle: isFolder ? null : Text('${(file['size'] / 1024)}'),
              onTap: () {
                if (isFolder) {
                  _loadFiles(file['path'] ?? file['name']);
                }
              },
            );
          },
        )
    );
  }
}