import 'dart:convert';
import 'dart:typed_data';
import 'package:encrypt/encrypt.dart' as enc;
import 'package:crypto/crypto.dart';

class MessageEncryption {
  late enc.Encrypter _encrypter;
  late enc.IV _iv;
  
  MessageEncryption() {
    // Key must be exactly 32 bytes for AES-256
    // The string is 31 chars — pad with \0 to 32 bytes (matches Python side)
    final keyStr = 'nexremote_encryption_key_32chars';
    final keyBytes = Uint8List(32);
    final strBytes = utf8.encode(keyStr);
    keyBytes.setRange(0, strBytes.length, strBytes);
    
    final key = enc.Key(keyBytes);
    // Fixed 16-byte zero IV (matches Python side)
    _iv = enc.IV(Uint8List(16));
    // Use CBC mode with PKCS7 padding to match Python's CBC + PKCS7
    _encrypter = enc.Encrypter(enc.AES(key, mode: enc.AESMode.cbc, padding: 'PKCS7'));
  }
  
  String encrypt(String data) {
    final encrypted = _encrypter.encrypt(data, iv: _iv);
    return encrypted.base64;
  }
  
  String decrypt(dynamic data) {
    try {
      String base64Str;
      if (data is String) {
        base64Str = data;
      } else if (data is List<int>) {
        base64Str = utf8.decode(data);
      } else {
        base64Str = data.toString();
      }
      
      final encrypted = enc.Encrypted.fromBase64(base64Str);
      return _encrypter.decrypt(encrypted, iv: _iv);
    } catch (e) {
      // If decryption fails, return raw string (might be plain JSON like auth responses)
      return data.toString();
    }
  }
}