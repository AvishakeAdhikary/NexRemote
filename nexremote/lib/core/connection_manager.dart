import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import '../security/encryption.dart';
import '../utils/logger.dart';

enum ConnectionState { disconnected, connecting, connected }

class ConnectionManager {
  WebSocketChannel? _channel;
  StreamController<ConnectionState> connectionStateController =
      StreamController<ConnectionState>.broadcast();
  StreamController<String> connectedDeviceController =
      StreamController<String>.broadcast();
  StreamController<Map<String, dynamic>> messageController =
      StreamController<Map<String, dynamic>>.broadcast();

  /// Stream for raw binary frames (screen capture, camera)
  StreamController<Uint8List> binaryMessageController =
      StreamController<Uint8List>.broadcast();

  final MessageEncryption _encryption = MessageEncryption();

  ConnectionState _state = ConnectionState.disconnected;
  String _deviceId = '';
  String _deviceName = '';

  // ── Reconnect state ──────────────────────────────────────────────────────
  bool _intentionalDisconnect = false;
  Timer? _reconnectTimer;
  int _reconnectAttempt = 0;
  static const int _maxReconnectAttempts = 15;
  static const Duration _maxBackoff = Duration(seconds: 30);

  // Stored for reconnect
  String? _lastHost;
  int? _lastSecurePort;
  int? _lastInsecurePort;

  // ── Keep-alive ping/pong ─────────────────────────────────────────────────
  Timer? _pingTimer;
  int _missedPongs = 0;
  static const int _maxMissedPongs = 3;
  static const Duration _pingInterval = Duration(seconds: 15);

  // ── Streams ──────────────────────────────────────────────────────────────

  Stream<ConnectionState> get connectionStateStream =>
      connectionStateController.stream;
  Stream<String> get connectedDeviceStream => connectedDeviceController.stream;
  Stream<Map<String, dynamic>> get messageStream => messageController.stream;

  /// Binary frame stream — screen/camera controllers listen to this
  Stream<Uint8List> get binaryMessageStream => binaryMessageController.stream;

  ConnectionState get state => _state;
  bool get isConnected => _state == ConnectionState.connected;

  // ── Connect ──────────────────────────────────────────────────────────────

  Future<bool> connect(
    String host,
    int securePort,
    int insecurePort,
    String deviceId,
    String deviceName, {
    bool trySecureFirst = true,
  }) async {
    _intentionalDisconnect = false;
    _reconnectAttempt = 0;

    // Store for reconnect
    _lastHost = host;
    _lastSecurePort = securePort;
    _lastInsecurePort = insecurePort;

    // Try secure connection first
    if (trySecureFirst) {
      Logger.info('Attempting secure connection (wss://)...');
      final secureSuccess = await _attemptConnection(
        host,
        securePort,
        deviceId,
        deviceName,
        useSecure: true,
      );
      if (secureSuccess) return true;

      Logger.warning(
        'Secure connection failed, falling back to non-secure (ws://)...',
      );
    }

    // Fallback to non-secure connection
    Logger.info('Attempting non-secure connection (ws://)...');
    return await _attemptConnection(
      host,
      insecurePort,
      deviceId,
      deviceName,
      useSecure: false,
    );
  }

  Future<bool> _attemptConnection(
    String host,
    int port,
    String deviceId,
    String deviceName, {
    required bool useSecure,
  }) async {
    try {
      _setState(ConnectionState.connecting);
      _deviceId = deviceId;
      _deviceName = deviceName;

      final protocol = useSecure ? 'wss' : 'ws';
      final wsUrl = Uri.parse('$protocol://$host:$port');

      Logger.info('Connecting to $wsUrl');

      // Create WebSocket with custom SSL handling for wss://
      if (useSecure) {
        final httpClient = HttpClient()
          ..badCertificateCallback =
              (X509Certificate cert, String host, int port) {
                Logger.warning(
                  'Accepting self-signed certificate for $host:$port',
                );
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
          .firstWhere(
            (msg) =>
                msg['type'] == 'auth_success' || msg['type'] == 'auth_failed',
          )
          .timeout(const Duration(seconds: 10));

      if (authResponse['type'] == 'auth_success') {
        _setState(ConnectionState.connected);
        connectedDeviceController.add(authResponse['server_name'] ?? 'PC');
        Logger.info('Connected successfully via $protocol');
        _reconnectAttempt = 0;

        // Keep screen/CPU alive while connected
        WakelockPlus.enable();

        // Start keep-alive ping
        _startPingTimer();

        return true;
      } else {
        throw Exception('Authentication failed');
      }
    } catch (e) {
      Logger.error(
        'Connection attempt failed (${useSecure ? "wss" : "ws"}): $e',
      );
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

  // ── Message handling ────────────────────────────────────────────────────

  void _handleMessage(dynamic message) {
    try {
      // Handle binary messages (screen/camera frames)
      if (message is List<int>) {
        final bytes = Uint8List.fromList(message);
        binaryMessageController.add(bytes);
        return;
      }

      // Handle text messages
      if (message is String) {
        // Try to parse as plain JSON first (auth responses are sent unencrypted)
        try {
          final data = jsonDecode(message) as Map<String, dynamic>;

          // Handle pong internally — don't bubble to consumers
          if (data['type'] == 'pong') {
            _missedPongs = 0;
            return;
          }

          messageController.add(data);
          return;
        } catch (_) {
          // Not plain JSON — must be encrypted base64
        }
      }

      // Decrypt the message (server encrypts all post-auth messages)
      final decrypted = _encryption.decrypt(message);
      final data = jsonDecode(decrypted) as Map<String, dynamic>;

      if (data['type'] == 'pong') {
        _missedPongs = 0;
        return;
      }

      messageController.add(data);
    } catch (e) {
      Logger.error('Error handling message: $e');
    }
  }

  void _handleError(error) {
    Logger.error('WebSocket error: $error');
    _cleanupConnection();
    _scheduleReconnect();
  }

  void _handleDisconnection() {
    Logger.info('WebSocket connection closed');
    _cleanupConnection();

    if (!_intentionalDisconnect) {
      Logger.info('Unintentional disconnect — scheduling reconnect...');
      _scheduleReconnect();
    } else {
      _setState(ConnectionState.disconnected);
    }
  }

  // ── Keep-alive ping ──────────────────────────────────────────────────────

  void _startPingTimer() {
    _stopPingTimer();
    _missedPongs = 0;
    _pingTimer = Timer.periodic(_pingInterval, (_) {
      if (_state != ConnectionState.connected || _channel == null) return;

      _missedPongs++;
      if (_missedPongs > _maxMissedPongs) {
        Logger.warning(
          'Missed $_missedPongs pongs — connection stale, reconnecting...',
        );
        _stopPingTimer();
        _cleanupConnection();
        _scheduleReconnect();
        return;
      }

      try {
        _sendRawJson({'type': 'ping'});
      } catch (e) {
        Logger.error('Failed to send ping: $e');
      }
    });
  }

  void _stopPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = null;
  }

  // ── Auto-reconnect ───────────────────────────────────────────────────────

  void _scheduleReconnect() {
    if (_intentionalDisconnect) return;
    if (_reconnectAttempt >= _maxReconnectAttempts) {
      Logger.error(
        'Max reconnect attempts reached ($_maxReconnectAttempts). Giving up.',
      );
      _setState(ConnectionState.disconnected);
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, ... capped at 30s
    final delaySeconds = (1 << _reconnectAttempt).clamp(
      1,
      _maxBackoff.inSeconds,
    );
    final delay = Duration(seconds: delaySeconds);
    _reconnectAttempt++;

    Logger.info(
      'Reconnect attempt $_reconnectAttempt/$_maxReconnectAttempts in ${delay.inSeconds}s...',
    );
    _setState(ConnectionState.connecting);

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, () async {
      if (_intentionalDisconnect) return;
      if (_lastHost == null) return;

      final success = await connect(
        _lastHost!,
        _lastSecurePort ?? 8765,
        _lastInsecurePort ?? 8766,
        _deviceId,
        _deviceName,
      );

      if (!success && !_intentionalDisconnect) {
        _scheduleReconnect();
      }
    });
  }

  void _cleanupConnection() {
    _stopPingTimer();
    try {
      _channel?.sink.close();
    } catch (_) {}
    _channel = null;
    WakelockPlus.disable();
  }

  // ── Send ──────────────────────────────────────────────────────────────────

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

  /// Send a plain JSON message (used for ping — not encrypted)
  void _sendRawJson(Map<String, dynamic> message) {
    try {
      _channel!.sink.add(jsonEncode(message));
    } catch (e) {
      Logger.error('Error sending raw JSON: $e');
    }
  }

  // ── Disconnect ────────────────────────────────────────────────────────────

  void disconnect() {
    _intentionalDisconnect = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _cleanupConnection();
    _setState(ConnectionState.disconnected);
  }

  void dispose() {
    disconnect();
    connectionStateController.close();
    connectedDeviceController.close();
    messageController.close();
    binaryMessageController.close();
  }
}
