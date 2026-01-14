import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:nexremote/models/control_command.dart';
import 'package:nexremote/models/pc_device.dart';

class NetworkService extends ChangeNotifier {
  Socket? _socket;
  bool _connected = false;
  String _pcName = '';
  String _pcAddress = '';
  final StreamController<Map<String, dynamic>> _messageController =
      StreamController<Map<String, dynamic>>.broadcast();
  bool get connected => _connected;
  String get pcName => _pcName;
  String get pcAddress => _pcAddress;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  Future<List<PCDevice>> discoverPCs() async {
    List<PCDevice> devices = [];
    try {
      final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      socket.broadcastEnabled = true;
      // Send discovery request
      final discoveryMsg = jsonEncode({'type': 'discover'});
      final data = utf8.encode(discoveryMsg);
      socket.send(data, InternetAddress('255.255.255.255'), 8889);
      // Listen for responses
      final completer = Completer<List<PCDevice>>();
      Timer(const Duration(seconds: 3), () {
        socket.close();
        if (!completer.isCompleted) {
          completer.complete(devices);
        }
      });
      socket.listen((event) {
        if (event == RawSocketEvent.read) {
          final packet = socket.receive();
          if (packet != null) {
            try {
              final message = utf8.decode(packet.data);
              final json = jsonDecode(message);
              if (json['type'] == 'discover_response') {
                final device = PCDevice(
                  name: json['name'] ?? 'Unknown PC',
                  ipAddress: packet.address.address,
                  port: json['port'] ?? 8888,
                  version: json['version'] ?? '1.0',
                );
                if (!devices.any((d) => d.ipAddress == device.ipAddress)) {
                  devices.add(device);
                }
              }
            } catch (e) {
              debugPrint('Error parsing discovery response: $e');
            }
          }
        }
      });
      return await completer.future;
    } catch (e) {
      debugPrint('Discovery error: $e');
      return devices;
    }
  }

  Future<bool> connectToPC(PCDevice device) async {
    try {
      _socket = await Socket.connect(device.ipAddress, device.port);
      _connected = true;
      _pcName = device.name;
      _pcAddress = device.ipAddress;
      // Listen for messages
      _socket!.listen(
        _handleData,
        onError: _handleError,
        onDone: _handleDone,
      );
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('Connection error: $e');
      _connected = false;
      notifyListeners();
      return false;
    }
  }

  void _handleData(data) {
    try {
      final message = utf8.decode(data);
      final lines = message.split('\n');
      for (final line in lines) {
        if (line.trim().isEmpty) continue;
        try {
          final json = jsonDecode(line);
          _messageController.add(json);
        } catch (e) {
          debugPrint('JSON decode error: $e');
        }
      }
    } catch (e) {
      debugPrint('Data handling error: $e');
    }
  }

  void _handleError(error) {
    debugPrint('Socket error: $error');
    disconnect();
  }

  void _handleDone() {
    debugPrint('Socket closed');
    disconnect();
  }

  void sendCommand(String type, [Map<String, dynamic>? data]) {
    if (!_connected || _socket == null) return;
    try {
      final command = ControlCommand(type: type, data: data ?? {});
      _socket!.write(command.toJson());
    } catch (e) {
      debugPrint('Send command error: $e');
    }
  }

  void disconnect() {
    _socket?.destroy();
    _socket = null;
    _connected = false;
    _pcName = '';
    _pcAddress = '';
    notifyListeners();
  }

  @override
  void dispose() {
    disconnect();
    _messageController.close();
    super.dispose();
  }
}
