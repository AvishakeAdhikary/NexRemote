import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:flutter/foundation.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'package:nexremote/models/control_command.dart';
import 'package:nexremote/models/pc_device.dart';

class NetworkService extends ChangeNotifier {
  Socket? _socket;
  bool _connected = false;
  bool _authenticated = false;
  String _pcName = '';
  String _pcAddress = '';
  bool _isUSB = false;
  encrypt.Encrypter? _encrypter;
  
  final StreamController<Map<String, dynamic>> _messageController = 
      StreamController<Map<String, dynamic>>.broadcast();
  
  bool get connected => _connected;
  bool get authenticated => _authenticated;
  String get pcName => _pcName;
  String get pcAddress => _pcAddress;
  bool get isUSB => _isUSB;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  
  Future<List<PCDevice>> discoverPCs() async {
    List<PCDevice> devices = [];
    
    debugPrint("=== DISCOVERY START ===");
    debugPrint("Starting PC discovery on port 8889...");
    
    try {
      // Create UDP socket for discovery
      final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      socket.broadcastEnabled = true;
      
      debugPrint("UDP socket created and bound to port ${socket.port}");
      
      // Prepare discovery message
      final discoveryMsg = jsonEncode({'type': 'discover'});
      final data = utf8.encode(discoveryMsg);
      
      debugPrint("Discovery message: $discoveryMsg");
      debugPrint("Message size: ${data.length} bytes");
      
      // Get local network information
      final info = NetworkInfo();
      String? wifiIP = await info.getWifiIP();
      String? wifiBroadcast = await info.getWifiBroadcast();
      String? wifiSubnet = await info.getWifiSubmask();
      
      debugPrint("Local WiFi IP: $wifiIP");
      debugPrint("WiFi Broadcast: $wifiBroadcast");
      debugPrint("WiFi Subnet: $wifiSubnet");
      
      // Calculate subnet broadcast if not available
      List<String> broadcastAddresses = ['255.255.255.255'];
      
      if (wifiIP != null) {
        final ipParts = wifiIP.split('.');
        if (ipParts.length == 4) {
          // Add subnet-specific broadcast
          final subnetBroadcast = '${ipParts[0]}.${ipParts[1]}.${ipParts[2]}.255';
          broadcastAddresses.add(subnetBroadcast);
          debugPrint("Calculated subnet broadcast: $subnetBroadcast");
        }
      }
      
      if (wifiBroadcast != null && !broadcastAddresses.contains(wifiBroadcast)) {
        broadcastAddresses.add(wifiBroadcast);
        debugPrint("Using WiFi broadcast address: $wifiBroadcast");
      }
      
      // Send to all broadcast addresses
      for (var broadcast in broadcastAddresses) {
        try {
          final sent = socket.send(
            data,
            InternetAddress(broadcast),
            8889,
          );
          debugPrint("✓ Sent $sent bytes to $broadcast:8889");
        } catch (e) {
          debugPrint("✗ Failed to send to $broadcast: $e");
        }
      }
      
      // Also try sending directly to common router addresses
      List<String> commonRouterIPs = [];
      if (wifiIP != null) {
        final parts = wifiIP.split('.');
        if (parts.length == 4) {
          // Try .1 and .254 (common router addresses)
          commonRouterIPs.add('${parts[0]}.${parts[1]}.${parts[2]}.1');
          commonRouterIPs.add('${parts[0]}.${parts[1]}.${parts[2]}.254');
          
          // Try scanning nearby IPs (same subnet)
          for (int i = 1; i < 255; i++) {
            commonRouterIPs.add('${parts[0]}.${parts[1]}.${parts[2]}.$i');
          }
        }
      }
      
      debugPrint("Trying ${commonRouterIPs.length} individual IPs...");
      
      int sentCount = 0;
      for (var ip in commonRouterIPs) {
        try {
          socket.send(data, InternetAddress(ip), 8889);
          sentCount++;
        } catch (e) {
          // Ignore errors for individual IPs
        }
      }
      
      debugPrint("Sent discovery to $sentCount IPs in subnet");
      
      // Listen for responses
      int responseCount = 0;
      
      socket.listen((event) {
        if (event == RawSocketEvent.read) {
          final packet = socket.receive();
          if (packet != null) {
            responseCount++;
            try {
              final message = utf8.decode(packet.data);
              debugPrint("[$responseCount] Received from ${packet.address.address}:${packet.port}");
              debugPrint("Response: $message");
              
              final json = jsonDecode(message);
              
              if (json['type'] == 'discover_response') {
                final device = PCDevice.fromJson(json, packet.address.address);
                
                if (!devices.any((d) => d.ipAddress == device.ipAddress)) {
                  devices.add(device);
                  debugPrint("✓ Found PC: ${device.name} at ${device.ipAddress}:${device.port}");
                }
              }
            } catch (e) {
              debugPrint("Error parsing response $responseCount: $e");
            }
          }
        }
      });
      
      // Wait for responses
      debugPrint("Waiting 5 seconds for responses...");
      await Future.delayed(const Duration(seconds: 5));
      
      socket.close();
      
      debugPrint("=== DISCOVERY END ===");
      debugPrint("Found ${devices.length} device(s)");
      
      return devices;
      
    } catch (e) {
      debugPrint('Discovery error: $e');
      debugPrint('Stack trace: ${StackTrace.current}');
      return devices;
    }
  }
  
  Future<bool> connectToPC(PCDevice device, String pairingCode) async {
    try {
      debugPrint("=== CONNECTION START ===");
      debugPrint("Connecting to ${device.ipAddress}:${device.port}...");
      debugPrint("Connection type: ${device.isUSB ? 'USB' : 'WiFi'}");
      
      _isUSB = device.isUSB;
      
      _socket = await Socket.connect(
        device.ipAddress,
        device.port,
        timeout: const Duration(seconds: 10),
      );
      
      debugPrint("✓ TCP connection established");
      
      // Perform handshake
      if (!await _performHandshake()) {
        debugPrint("✗ Handshake failed");
        disconnect();
        return false;
      }
      
      debugPrint("✓ Handshake successful");
      
      // Authenticate
      if (!await _authenticate(pairingCode, device.name)) {
        debugPrint("✗ Authentication failed");
        disconnect();
        return false;
      }
      
      debugPrint("✓ Authentication successful");
      
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
      
      debugPrint("=== CONNECTION SUCCESS ===");
      notifyListeners();
      return true;
      
    } catch (e) {
      debugPrint('Connection error: $e');
      debugPrint('Stack trace: ${StackTrace.current}');
      _connected = false;
      _authenticated = false;
      notifyListeners();
      return false;
    }
  }
  
  Future<bool> _performHandshake() async {
    try {
      final completer = Completer<bool>();
      StreamSubscription? subscription;
      
      subscription = _socket!.listen((data) {
        try {
          final message = utf8.decode(data);
          debugPrint("Handshake received: $message");
          final json = jsonDecode(message.trim());
          
          if (json['type'] == 'handshake') {
            final keyStr = json['key'] as String;
            final key = encrypt.Key.fromUtf8(keyStr.padRight(32).substring(0, 32));
            _encrypter = encrypt.Encrypter(encrypt.Fernet(key));
            
            debugPrint("Encryption key received and set");
            
            // Send acknowledgment
            final ack = jsonEncode({'type': 'handshake_ack'}) + '\n';
            _socket!.add(utf8.encode(ack));
            debugPrint("Handshake ACK sent");
            
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
          debugPrint("Handshake timeout");
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
      debugPrint("Starting authentication with code: $pairingCode");
      
      final completer = Completer<bool>();
      StreamSubscription? subscription;
      
      subscription = _socket!.listen((data) {
        try {
          final encrypted = data;
          final encryptedStr = String.fromCharCodes(encrypted.where((b) => b != 10));
          
          if (encryptedStr.isEmpty) return;
          
          final decrypted = _encrypter!.decrypt64(encryptedStr);
          final json = jsonDecode(decrypted);
          
          debugPrint("Auth message received: ${json['type']}");
          
          if (json['type'] == 'auth_request') {
            debugPrint("Auth request received, sending credentials...");
            
            // Send auth response
            final authData = {
              'type': 'auth_response',
              'pairing_code': pairingCode,
              'device_name': deviceName,
            };
            
            _sendEncrypted(authData);
            
          } else if (json['type'] == 'auth_success') {
            debugPrint("✓ Authentication successful");
            subscription?.cancel();
            completer.complete(true);
            
          } else if (json['type'] == 'auth_failed') {
            debugPrint("✗ Authentication failed: ${json['reason']}");
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
          debugPrint("Authentication timeout");
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
      _socket!.add(utf8.encode(encrypted.base64) + [10]);
      debugPrint("Encrypted message sent: ${data['type']}");
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
    _isUSB = false;
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