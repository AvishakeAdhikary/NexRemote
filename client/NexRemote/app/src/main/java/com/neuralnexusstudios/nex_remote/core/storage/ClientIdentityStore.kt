package com.neuralnexusstudios.nex_remote.core.storage

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.Base64

class ClientIdentityStore(context: Context) {
    private val prefs = context.getSharedPreferences("nexremote_client_identity", Context.MODE_PRIVATE)

    val publicKeyBase64: String
        get() = ensureKeyPair().public.encoded.toBase64()

    fun signNonce(nonce: ByteArray): String {
        val keyPair = ensureKeyPair()
        val signature = Signature.getInstance(SIGNATURE_ALGORITHM)
        signature.initSign(keyPair.private)
        signature.update(nonce)
        return signature.sign().toBase64()
    }

    private fun ensureKeyPair(): KeyPair {
        val alias = prefs.getString(KEY_ALIAS, DEFAULT_ALIAS) ?: DEFAULT_ALIAS
        val keyStore = KeyStore.getInstance(ANDROID_KEY_STORE).apply { load(null) }
        val existing = keyStore.getEntry(alias, null) as? KeyStore.PrivateKeyEntry
        if (existing != null) {
            return KeyPair(existing.certificate.publicKey, existing.privateKey)
        }

        val generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, ANDROID_KEY_STORE)
        generator.initialize(
            KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setAlgorithmParameterSpec(ECGenParameterSpec(CURVE_NAME))
                .setUserAuthenticationRequired(false)
                .build(),
        )
        val keyPair = generator.generateKeyPair()
        prefs.edit().putString(KEY_ALIAS, alias).apply()
        return keyPair
    }

    private fun ByteArray.toBase64(): String = Base64.getEncoder().encodeToString(this)

    companion object {
        private const val DEFAULT_ALIAS = "nexremote_client_identity"
        private const val KEY_ALIAS = "client_identity_alias"
        private const val ANDROID_KEY_STORE = "AndroidKeyStore"
        private const val CURVE_NAME = "secp256r1"
        private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
    }
}
