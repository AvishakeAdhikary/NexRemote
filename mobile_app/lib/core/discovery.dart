import 'dart:io';
import 'dart:async';
import 'dart:convert';
import '../utils/logger.dart';

class DiscoveryService {
  static const int discoveryPort = 37020;
  static const String magicBytes = 'NEXREMOTE_DISCOVER';
  
  Future<List<ServerInfo>> discoverServers({Duration timeout = const Duration(seconds: 5)}) async {
    final servers = <ServerInfo>[];
    
    try {
      // Create UDP socket
      final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      socket.broadcastEnabled = true;
      
      // Send broadcast
      final request = utf8.encode(magicBytes);
      socket.send(request, InternetAddress('255.255.255.255'), discoveryPort);
      
      Logger.info('Sent discovery broadcast');
      
      // Listen for responses
      final completer = Completer<List<ServerInfo>>();
      
      socket.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          final datagram = socket.receive();
          if (datagram != null) {
            try {
              final response = utf8.decode(datagram.data);
              final data = jsonDecode(response);
                            if (data['type'] == 'discovery_response') {
                final server = ServerInfo(
                  name: data['name'] ?? 'Unknown PC',
                  address: datagram.address.address,
                  port: data['port'] ?? 8765,
                  portInsecure: data['port_insecure'] ?? 8766,
                  id: data['id'] ?? '',
                  version: data['version'] ?? '1.0.0',
                );
                
                // Avoid duplicates
                if (!servers.any((s) => s.id == server.id)) {
                  servers.add(server);
                  Logger.info('Found server: ${server.name} at ${server.address}');
                }
              }
            } catch (e) {
              Logger.error('Error parsing discovery response: $e');
            }
          }
        }
      });
      
      // Timeout
      Future.delayed(timeout, () {
        if (!completer.isCompleted) {
          socket.close();
          completer.complete(servers);
        }
      });
      
      return completer.future;
      
    } catch (e) {
      Logger.error('Discovery error: $e');
      return [];
    }
  }
}

class ServerInfo {
  final String name;
  final String address;
  final int port;
  final int portInsecure;
  final String id;
  final String version;
  
  ServerInfo({
    required this.name,
    required this.address,
    required this.port,
    required this.portInsecure,
    required this.id,
    required this.version,
  });
}