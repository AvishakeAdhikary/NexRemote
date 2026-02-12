import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';
import '../security/encryption.dart';
import '../utils/logger.dart';

enum ConnectionState {
  disconnected,
  connecting,
  connected,
}

class ConnectionManager {
  WebSocketChannel? _channel;
  StreamController<ConnectionState> connectionStateController =
      StreamController<ConnectionState>.broadcast();
  StreamController<String> connectedDeviceController =
      StreamController<String>.broadcast();
  StreamController<Map<String, dynamic>> messageController =
      StreamController<Map<String, dynamic>>.broadcast();

  final MessageEncryption _encryption = MessageEncryption();
  
  ConnectionState _state = ConnectionState.disconnected;
  String _deviceId = '';
  String _deviceName = '';
  bool _useSecure = false;

  Stream<ConnectionState> get connectionStateStream =>
      connectionStateController.stream;
  Stream<String> get connectedDeviceStream =>
      connectedDeviceController.stream;
  Stream<Map<String, dynamic>> get messageStream => messageController.stream;

  ConnectionState get state => _state;
  bool get isConnected => _state == ConnectionState.connected;

  Future<bool> connect(
    String host, 
    int securePort,
    int insecurePort,
    String deviceId, 
    String deviceName,
    {bool trySecureFirst = true}
  ) async {
    // Try secure connection first
    if (trySecureFirst) {
      Logger.info('Attempting secure connection (wss://)...');
      final secureSuccess = await _attemptConnection(
        host, 
        securePort, 
        deviceId, 
        deviceName, 
        useSecure: true
      );
      if (secureSuccess) return true;
      
      Logger.warning('Secure connection failed, falling back to non-secure (ws://)...');
    }
    
    // Fallback to non-secure connection
    Logger.info('Attempting non-secure connection (ws://)...');
    return await _attemptConnection(
      host, 
      insecurePort, 
      deviceId, 
      deviceName, 
      useSecure: false
    );
  }

  Future<bool> _attemptConnection(
    String host,
    int port,
    String deviceId,
    String deviceName,
    {required bool useSecure}
  ) async {
    try {
      _setState(ConnectionState.connecting);
      _deviceId = deviceId;
      _deviceName = deviceName;
      _useSecure = useSecure;

      final protocol = useSecure ? 'wss' : 'ws';
      final wsUrl = Uri.parse('$protocol://$host:$port');
      
      Logger.info('Connecting to $wsUrl');
      
      // Create WebSocket with custom SSL handling for wss://
      if (useSecure) {
        final httpClient = HttpClient()
          ..badCertificateCallback = (X509Certificate cert, String host, int port) {
            Logger.warning('Accepting self-signed certificate for $host:$port');
            return true;
          };
        
        final request = await httpClient.getUrl(wsUrl);
        request.headers.add('Connection', 'Upgrade');
        request.headers.add('Upgrade', 'websocket');
        request.headers.add('Sec-WebSocket-Version', '13');
        request.headers.add('Sec-WebSocket-Key', _generateWebSocketKey());
        
        final response = await request.close();
        final socket = await response.detachSocket();
        
        _channel = IOWebSocketChannel(
          WebSocket.fromUpgradedSocket(socket, serverSide: false),
        );
      } else {
        _channel = IOWebSocketChannel.connect(wsUrl);
      }

      // Set shorter timeout for fallback attempts
      await _channel!.ready.timeout(const Duration(seconds: 5));

      // Send auth message (plain JSON)
      final authMessage = {
        'type': 'auth',
        'device_id': deviceId,
        'device_name': deviceName,
        'version': '1.0.0',
      };

      _channel!.sink.add(jsonEncode(authMessage));
      Logger.info('Sent auth message (plain JSON)');

      // Listen for messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnection,
      );

      // Wait for auth response
      final authResponse = await messageStream
          .firstWhere((msg) => msg['type'] == 'auth_success' || msg['type'] == 'auth_failed')
          .timeout(const Duration(seconds: 10));

      if (authResponse['type'] == 'auth_success') {
        _setState(ConnectionState.connected);
        connectedDeviceController.add(authResponse['server_name'] ?? 'PC');
        Logger.info('Connected successfully via $protocol');
        return true;
      } else {
        throw Exception('Authentication failed');
      }
    } catch (e) {
      Logger.error('Connection attempt failed (${useSecure ? "wss" : "ws"}): $e');
      _setState(ConnectionState.disconnected);
      _channel?.sink.close();
      _channel = null;
      return false;
    }
  }
  
  String _generateWebSocketKey() {
    final random = DateTime.now().millisecondsSinceEpoch.toString();
    final bytes = utf8.encode(random);
    return base64.encode(bytes);
  }

  void _handleMessage(dynamic message) {
    try {
      String decrypted;
      
      if (message is String) {
        decrypted = message;
      } else {
        decrypted = _encryption.decrypt(message);
      }

      final data = jsonDecode(decrypted) as Map<String, dynamic>;
      messageController.add(data);
    } catch (e) {
      Logger.error('Error handling message: $e');
    }
  }

  void _handleError(error) {
    Logger.error('WebSocket error: $error');
    disconnect();
  }

  void _handleDisconnection() {
    Logger.info('Disconnected from server');
    _setState(ConnectionState.disconnected);
  }

  void _setState(ConnectionState state) {
    _state = state;
    connectionStateController.add(state);
  }

  void sendMessage(Map<String, dynamic> message) {
    if (_channel == null || _state != ConnectionState.connected) {
      Logger.warning('Cannot send message: not connected');
      return;
    }

    _sendMessage(message);
  }

  void _sendMessage(Map<String, dynamic> message) {
    try {
      final jsonStr = jsonEncode(message);
      final encrypted = _encryption.encrypt(jsonStr);
      _channel!.sink.add(encrypted);
    } catch (e) {
      Logger.error('Error sending message: $e');
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _setState(ConnectionState.disconnected);
  }

  void dispose() {
    disconnect();
    connectionStateController.close();
    connectedDeviceController.close();
    messageController.close();
  }
}