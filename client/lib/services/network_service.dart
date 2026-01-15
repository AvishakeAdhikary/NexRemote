import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:flutter/foundation.dart';
import 'package:nexremote/models/control_command.dart';
import 'package:nexremote/models/pc_device.dart';

class NetworkService extends ChangeNotifier {
  Socket? _socket;
  bool _connected = false;
  bool _authenticated = false;
  String _pcName = '';
  String _pcAddress = '';
  encrypt.Encrypter? _encrypter;
  
  final StreamController<Map<String, dynamic>> _messageController = 
      StreamController<Map<String, dynamic>>.broadcast();
  
  bool get connected => _connected;
  bool get authenticated => _authenticated;
  String get pcName => _pcName;
  String get pcAddress => _pcAddress;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  
  Future<List<PCDevice>> discoverPCs() async {
    List<PCDevice> devices = [];
    
    debugPrint("Starting PC discovery...");
    
    try {
      final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      socket.broadcastEnabled = true;
      
      // Send discovery request
      final discoveryMsg = jsonEncode({'type': 'discover'});
      final data = utf8.encode(discoveryMsg);
      
      debugPrint("Sending broadcast to port 8889...");
      
      // Send to broadcast address
      final sent = socket.send(
        data,
        InternetAddress('255.255.255.255'),
        8889,
      );
      
      debugPrint("Broadcast sent: $sent bytes");
      
      // Also try sending to local subnet
      try {
        final interfaces = await NetworkInterface.list();
        for (var interface in interfaces) {
          for (var addr in interface.addresses) {
            if (addr.type == InternetAddressType.IPv4) {
              final ip = addr.address;
              final parts = ip.split('.');
              if (parts.length == 4) {
                final broadcast = '${parts[0]}.${parts[1]}.${parts[2]}.255';
                socket.send(data, InternetAddress(broadcast), 8889);
                debugPrint("Sent to subnet broadcast: $broadcast");
              }
            }
          }
        }
      } catch (e) {
        debugPrint("Error getting interfaces: $e");
      }
      
      // Listen for responses
      final completer = Completer<List<PCDevice>>();
      
      socket.listen((event) {
        if (event == RawSocketEvent.read) {
          final packet = socket.receive();
          if (packet != null) {
            try {
              final message = utf8.decode(packet.data);
              debugPrint("Received response: $message from ${packet.address.address}");
              
              final json = jsonDecode(message);
              
              if (json['type'] == 'discover_response') {
                final device = PCDevice.fromJson(json, packet.address.address);
                
                if (!devices.any((d) => d.ipAddress == device.ipAddress)) {
                  devices.add(device);
                  debugPrint("Found PC: ${device.name} at ${device.ipAddress}");
                }
              }
            } catch (e) {
              debugPrint('Error parsing discovery response: $e');
            }
          }
        }
      });
      
      // Wait for responses
      Timer(const Duration(seconds: 3), () {
        socket.close();
        if (!completer.isCompleted) {
          completer.complete(devices);
        }
      });
      
      return await completer.future;
      
    } catch (e) {
      debugPrint('Discovery error: $e');
      return devices;
    }
  }
  
  Future<bool> connectToPC(PCDevice device, String pairingCode) async {
    try {
      debugPrint("Connecting to ${device.ipAddress}:${device.port}...");
      
      _socket = await Socket.connect(
        device.ipAddress,
        device.port,
        timeout: const Duration(seconds: 10),
      );
      
      debugPrint("TCP connection established");
      
      // Perform handshake
      if (!await _performHandshake()) {
        debugPrint("Handshake failed");
        disconnect();
        return false;
      }
      
      debugPrint("Handshake successful");
      
      // Authenticate
      if (!await _authenticate(pairingCode, device.name)) {
        debugPrint("Authentication failed");
        disconnect();
        return false;
      }
      
      debugPrint("Authentication successful");
      
      _connected = true;
      _authenticated = true;
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
      _authenticated = false;
      notifyListeners();
      return false;
    }
  }
  
  Future<bool> _performHandshake() async {
    try {
      // Wait for handshake from server
      final completer = Completer<bool>();
      StreamSubscription? subscription;
      
      subscription = _socket!.listen((data) {
        try {
          final message = utf8.decode(data);
          final json = jsonDecode(message.trim());
          
          if (json['type'] == 'handshake') {
            final keyStr = json['key'] as String;
            final key = encrypt.Key.fromUtf8(keyStr.padRight(32).substring(0, 32));
            _encrypter = encrypt.Encrypter(encrypt.Fernet(key));
            
            // Send acknowledgment
            final ack = jsonEncode({'type': 'handshake_ack'}) + '\n';
            _socket!.add(utf8.encode(ack));
            
            subscription?.cancel();
            completer.complete(true);
          }
        } catch (e) {
          debugPrint("Handshake parse error: $e");
        }
      });
      
      // Timeout
      Timer(const Duration(seconds: 10), () {
        if (!completer.isCompleted) {
          subscription?.cancel();
          completer.complete(false);
        }
      });
      
      return await completer.future;
      
    } catch (e) {
      debugPrint("Handshake error: $e");
      return false;
    }
  }
  
  Future<bool> _authenticate(String pairingCode, String deviceName) async {
    try {
      final completer = Completer<bool>();
      StreamSubscription? subscription;
      
      subscription = _socket!.listen((data) {
        try {
          final encrypted = data;
          final decrypted = _encrypter!.decrypt64(
            String.fromCharCodes(encrypted.where((b) => b != 10)), // Remove newline
          );
          final json = jsonDecode(decrypted);
          
          if (json['type'] == 'auth_request') {
            // Send auth response
            final authData = {
              'type': 'auth_response',
              'pairing_code': pairingCode,
              'device_name': deviceName,
            };
            
            _sendEncrypted(authData);
            
          } else if (json['type'] == 'auth_success') {
            subscription?.cancel();
            completer.complete(true);
            
          } else if (json['type'] == 'auth_failed') {
            subscription?.cancel();
            completer.complete(false);
          }
        } catch (e) {
          debugPrint("Auth parse error: $e");
        }
      });
      
      // Timeout
      Timer(const Duration(seconds: 30), () {
        if (!completer.isCompleted) {
          subscription?.cancel();
          completer.complete(false);
        }
      });
      
      return await completer.future;
      
    } catch (e) {
      debugPrint("Authentication error: $e");
      return false;
    }
  }
  
  void _sendEncrypted(Map<String, dynamic> data) {
    if (_encrypter == null || _socket == null) return;
    
    try {
      final jsonStr = jsonEncode(data);
      final encrypted = _encrypter!.encrypt(jsonStr);
      _socket!.add(utf8.encode(encrypted.base64) + [10]); // Add newline
    } catch (e) {
      debugPrint("Send encrypted error: $e");
    }
  }
  
  void _handleData(data) {
    if (!_authenticated) return;
    
    try {
      final encrypted = data;
      final encryptedStr = String.fromCharCodes(encrypted.where((b) => b != 10));
      
      if (encryptedStr.isEmpty) return;
      
      final decrypted = _encrypter!.decrypt64(encryptedStr);
      final json = jsonDecode(decrypted);
      
      _messageController.add(json);
      
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
    if (!_connected || !_authenticated || _socket == null) return;
    
    try {
      final command = {'type': type, 'data': data ?? {}};
      _sendEncrypted(command);
    } catch (e) {
      debugPrint('Send command error: $e');
    }
  }
  
  void disconnect() {
    _socket?.destroy();
    _socket = null;
    _connected = false;
    _authenticated = false;
    _pcName = '';
    _pcAddress = '';
    _encrypter = null;
    notifyListeners();
  }
  
  @override
  void dispose() {
    disconnect();
    _messageController.close();
    super.dispose();
  }
}