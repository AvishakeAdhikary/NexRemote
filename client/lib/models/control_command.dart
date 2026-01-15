import 'dart:convert';

class ControlCommand {
  final String type;
  final Map<String, dynamic> data;

  ControlCommand({required this.type, this.data = const {}});

  String toJson() {
    return '${jsonEncode({'type': type, 'data': data})}\n';
  }
}