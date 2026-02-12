import 'dart:convert';
import 'dart:typed_data';
import 'package:encrypt/encrypt.dart' as enc;
import 'package:crypto/crypto.dart';

class MessageEncryption {
  late enc.Encrypter _encrypter;
  late enc.IV _iv;
  
  MessageEncryption() {
    // In production, use secure key storage
    final key = enc.Key.fromUtf8('nexremote_encryption_key_32chars');
    _iv = enc.IV.fromLength(16);
    _encrypter = enc.Encrypter(enc.AES(key));
  }
  
  String encrypt(String data) {
    final encrypted = _encrypter.encrypt(data, iv: _iv);
    return encrypted.base64;
  }
  
  String decrypt(dynamic data) {
    if (data is String) {
      // Already decrypted or plain JSON
      return data;
    }
    
    try {
      final encrypted = enc.Encrypted.fromBase64(data.toString());
      return _encrypter.decrypt(encrypted, iv: _iv);
    } catch (e) {
      // If decryption fails, assume it's plain text
      return data.toString();
    }
  }
}