import 'dart:io';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/logger.dart';

class CertificateManager {
  static const String _certFingerprintKey = 'server_cert_fingerprint';
  
  late SharedPreferences _prefs;
  
  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }
  
  /// Validate server certificate
  bool validateCertificate(X509Certificate certificate, String host) {
    try {
      // Get certificate fingerprint
      final fingerprint = _getCertificateFingerprint(certificate);
      
      // Check if we've seen this certificate before
      final storedFingerprint = _prefs.getString(_certFingerprintKey);
      
      if (storedFingerprint == null) {
        // First time seeing this server - store fingerprint
        _prefs.setString(_certFingerprintKey, fingerprint);
        Logger.info('Stored new server certificate fingerprint');
        return true;
      }
      
      // Check if fingerprint matches
      if (storedFingerprint == fingerprint) {
        Logger.debug('Certificate fingerprint verified');
        return true;
      } else {
        Logger.warning('Certificate fingerprint mismatch!');
        return false;
      }
      
    } catch (e) {
      Logger.error('Certificate validation error: $e');
      return false;
    }
  }
  
  String _getCertificateFingerprint(X509Certificate certificate) {
    // Get SHA-256 fingerprint of certificate
    // Note: dart:io doesn't provide direct access to fingerprint
    // This is a simplified version - in production, use proper crypto library
    return certificate.pem.hashCode.toString();
  }
  
  /// Clear stored certificate (for re-pairing)
  Future<void> clearStoredCertificate() async {
    await _prefs.remove(_certFingerprintKey);
    Logger.info('Cleared stored certificate');
  }
  
  /// Check if server certificate is trusted
  bool isCertificateTrusted(String host) {
    return _prefs.containsKey(_certFingerprintKey);
  }
  
  /// Get certificate info for display
  Map<String, String>? getCertificateInfo() {
    final fingerprint = _prefs.getString(_certFingerprintKey);
    
    if (fingerprint != null) {
      return {
        'fingerprint': fingerprint,
        'status': 'Trusted',
      };
    }
    
    return null;
  }
}