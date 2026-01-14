class PCDevice {
  final String name;
  final String ipAddress;
  final int port;
  final String version;

  PCDevice({
    required this.name,
    required this.ipAddress,
    required this.port,
    required this.version,
  });

  factory PCDevice.fromJson(Map<String, dynamic> json) {
    return PCDevice(
      name: json['name'] ?? 'Unknown PC',
      ipAddress: json['ip'] ?? '',
      port: json['port'] ?? 8888,
      version: json['version'] ?? '1.0',
    );
  }
}