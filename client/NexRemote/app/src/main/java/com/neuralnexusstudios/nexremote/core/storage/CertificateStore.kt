package com.neuralnexusstudios.nexremote.core.storage

import android.content.Context
import java.security.MessageDigest
import java.security.cert.Certificate

class CertificateStore(context: Context) {
    private val prefs = context.getSharedPreferences("nexremote_cert_store", Context.MODE_PRIVATE)

    fun trustOrVerify(host: String, certificate: Certificate): Boolean {
        val key = "fingerprint_$host"
        val fingerprint = fingerprint(certificate)
        val existing = prefs.getString(key, null)
        return if (existing == null) {
            prefs.edit().putString(key, fingerprint).apply()
            true
        } else {
            existing == fingerprint
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
}
