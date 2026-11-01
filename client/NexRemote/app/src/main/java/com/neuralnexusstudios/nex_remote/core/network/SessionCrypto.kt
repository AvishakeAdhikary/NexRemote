package com.neuralnexusstudios.nex_remote.core.network

import java.math.BigInteger
import java.nio.charset.StandardCharsets
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.interfaces.ECPrivateKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECPrivateKeySpec
import java.security.spec.X509EncodedKeySpec
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyAgreement
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Protocol v2 session encryption, negotiated during auth (see root AGENTS.md).
 *
 * Must match windows_app/server/src/nexremote_server/protocol/v2_crypto.py exactly:
 * ECDH P-256 -> HKDF-SHA256(salt = SHA-256(client_spki || server_spki), info "nexremote/v2/c2s"|"s2c")
 * -> AES-256-GCM, nonce = 4 zero bytes || 8-byte big-endian per-direction counter,
 * wire text = Base64(ciphertext || tag).
 */
object SessionCrypto {
    const val PROTOCOL_VERSION = 2
    const val SESSION_CRYPTO = "aes-256-gcm"
    private val INFO_C2S = "nexremote/v2/c2s".toByteArray(StandardCharsets.US_ASCII)
    private val INFO_S2C = "nexremote/v2/s2c".toByteArray(StandardCharsets.US_ASCII)

    fun generateEphemeral(): KeyPair =
        KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()

    fun publicKeyBase64(keyPair: KeyPair): String = Base64.getEncoder().encodeToString(keyPair.public.encoded)

    /** Returns (k_c2s, k_s2c) from the client's ephemeral private key and both SPKIs. */
    fun deriveClientKeys(clientPrivate: PrivateKey, clientSpkiB64: String, serverSpkiB64: String): Pair<ByteArray, ByteArray> {
        val clientSpki = Base64.getDecoder().decode(clientSpkiB64)
        val serverSpki = Base64.getDecoder().decode(serverSpkiB64)
        val serverPublic = KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(serverSpki))
        val shared = KeyAgreement.getInstance("ECDH").run {
            init(clientPrivate)
            doPhase(serverPublic, true)
            generateSecret()
        }
        val salt = MessageDigest.getInstance("SHA-256").digest(clientSpki + serverSpki)
        return hkdf(shared, salt, INFO_C2S, 32) to hkdf(shared, salt, INFO_S2C, 32)
    }

    /** RFC 5869 HKDF-SHA256. */
    fun hkdf(ikm: ByteArray, salt: ByteArray, info: ByteArray, length: Int): ByteArray {
        val prk = Mac.getInstance("HmacSHA256").run {
            init(SecretKeySpec(if (salt.isEmpty()) ByteArray(32) else salt, "HmacSHA256"))
            doFinal(ikm)
        }
        val out = ByteArray(length)
        var previous = ByteArray(0)
        var offset = 0
        var counter = 1
        while (offset < length) {
            previous = Mac.getInstance("HmacSHA256").run {
                init(SecretKeySpec(prk, "HmacSHA256"))
                update(previous)
                update(info)
                update(counter.toByte())
                doFinal()
            }
            val take = minOf(previous.size, length - offset)
            previous.copyInto(out, offset, 0, take)
            offset += take
            counter++
        }
        return out
    }

    /** Test helper: a P-256 private key from a raw scalar, using a generated key's curve parameters. */
    internal fun privateKeyFromScalar(scalar: BigInteger): PrivateKey {
        val params = (generateEphemeral().private as ECPrivateKey).params
        return KeyFactory.getInstance("EC").generatePrivate(ECPrivateKeySpec(scalar, params))
    }
}

interface MessageCipher {
    val name: String
    fun encrypt(plaintext: String): String
    fun decrypt(payload: String): String
}

object LegacyMessageCipher : MessageCipher {
    override val name = "legacy"
    override fun encrypt(plaintext: String): String = CryptoUtils.encryptToBase64(plaintext)
    override fun decrypt(payload: String): String = CryptoUtils.decryptBase64(payload)
}

class SessionCipher(sendKey: ByteArray, recvKey: ByteArray) : MessageCipher {
    override val name = "v2"
    private val sendKeySpec = SecretKeySpec(sendKey, "AES")
    private val recvKeySpec = SecretKeySpec(recvKey, "AES")
    private var sendCounter = 0L
    private var recvCounter = 0L
    private val sendLock = Any()
    private val recvLock = Any()

    /** Callers must hand the result to the socket in the same order encrypt() was called. */
    override fun encrypt(plaintext: String): String = synchronized(sendLock) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, sendKeySpec, GCMParameterSpec(128, nonce(sendCounter)))
        sendCounter++
        Base64.getEncoder().encodeToString(cipher.doFinal(plaintext.toByteArray(StandardCharsets.UTF_8)))
    }

    override fun decrypt(payload: String): String = synchronized(recvLock) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, recvKeySpec, GCMParameterSpec(128, nonce(recvCounter)))
        val plain = cipher.doFinal(Base64.getDecoder().decode(payload.trim()))
        recvCounter++
        plain.toString(StandardCharsets.UTF_8)
    }

    private fun nonce(counter: Long): ByteArray =
        ByteArray(12).also { bytes -> for (i in 0 until 8) bytes[11 - i] = (counter ushr (8 * i)).toByte() }

    companion object {
        fun forClient(kC2s: ByteArray, kS2c: ByteArray) = SessionCipher(sendKey = kC2s, recvKey = kS2c)
    }
}
