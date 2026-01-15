class PCDevice {
  final String name;
  final String ipAddress;
  final int port;
  final String version;
  final bool requiresPairing;
  final bool isUSB;

  PCDevice({
    required this.name,
    required this.ipAddress,
    required this.port,
    required this.version,
    this.requiresPairing = true,
    this.isUSB = false,
  });

  factory PCDevice.fromJson(Map<String, dynamic> json, String ip) {
    return PCDevice(
      name: json['name'] ?? 'Unknown PC',
      ipAddress: ip,
      port: json['port'] ?? 8888,
      version: json['version'] ?? '1.0',
      requiresPairing: json['requires_pairing'] ?? true,
      isUSB: false,
    );
  }
  
  factory PCDevice.usb(String name) {
    return PCDevice(
      name: name,
      ipAddress: '127.0.0.1',  // Localhost for ADB forwarding
      port: 8888,
      version: '1.0',
      requiresPairing: true,
      isUSB: true,
    );
  }
}