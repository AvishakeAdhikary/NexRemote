package com.neuralnexusstudios.nex_remote.core.network

import com.neuralnexusstudios.nex_remote.core.storage.CertificateStore
import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSession
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.X509TrustManager

/**
 * Trust for the PC's self-signed certificate: trust-on-first-use pinning of its SHA-256
 * fingerprint per host, or the fingerprint from discovery/QR when one is known.
 *
 * The check happens inside the TLS handshake (no trust-all manager), and the hostname check
 * accepts a session only when its peer certificate is the pinned one. The PC's certificate is
 * issued to "localhost", so a regular hostname match cannot apply.
 */
class PinnedTrust(
    private val host: String,
    private val expectedFingerprint: String?,
    private val certificateStore: CertificateStore,
) {
    @Volatile
    var rejected: Boolean = false
        private set

    val trustManager: X509TrustManager = object : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {
            throw CertificateException("Client certificates are not used")
        }

        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
            val leaf = chain?.firstOrNull() ?: throw CertificateException("Empty certificate chain")
            leaf.checkValidity()
            if (!certificateStore.trustOrVerify(host, leaf, expectedFingerprint)) {
                rejected = true
                throw CertificateException("Certificate for $host does not match the paired PC")
            }
        }

        override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }

    val hostnameVerifier = HostnameVerifier { _, session: SSLSession ->
        val leaf = runCatching { session.peerCertificates.firstOrNull() as? X509Certificate }.getOrNull()
        leaf != null && certificateStore.isPinned(host, leaf)
    }

    val socketFactory: SSLSocketFactory by lazy {
        SSLContext.getInstance("TLS").apply { init(null, arrayOf(trustManager), SecureRandom()) }.socketFactory
    }
}
