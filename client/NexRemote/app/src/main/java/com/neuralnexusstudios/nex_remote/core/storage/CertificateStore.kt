package com.neuralnexusstudios.nex_remote.core.storage

import android.content.Context
import java.security.MessageDigest
import java.security.cert.Certificate

class CertificateStore(context: Context) {
    private val prefs = context.getSharedPreferences("nexremote_cert_store", Context.MODE_PRIVATE)

    fun trustOrVerify(host: String, certificate: Certificate, expectedFingerprint: String? = null): Boolean {
        val key = "fingerprint_$host"
        val fingerprint = normalizeFingerprint(fingerprint(certificate))
        val existing = prefs.getString(key, null)?.let(::normalizeFingerprint)
        val expected = expectedFingerprint?.takeIf { it.isNotBlank() }?.let(::normalizeFingerprint)
        if (expected != null && expected != fingerprint) {
            return false
        }

        return if (existing == null) {
            prefs.edit().putString(key, fingerprint).apply()
            true
        } else if (existing == fingerprint) {
            true
        } else if (expected != null && expected == fingerprint) {
            // Discovery / QR fingerprint matched the presented certificate,
            // so treat this as an intentional certificate rotation and update the stored pin.
            prefs.edit().putString(key, fingerprint).apply()
            true
        } else {
            false
        }
    }

    fun clear(host: String) {
        prefs.edit().remove("fingerprint_$host").apply()
    }

    private fun fingerprint(certificate: Certificate): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val bytes = digest.digest(certificate.encoded)
        return bytes.joinToString(":") { "%02X".format(it) }
    }

    private fun normalizeFingerprint(value: String): String =
        value.uppercase()
            .replace(":", "")
            .replace("-", "")
            .replace(" ", "")
}
