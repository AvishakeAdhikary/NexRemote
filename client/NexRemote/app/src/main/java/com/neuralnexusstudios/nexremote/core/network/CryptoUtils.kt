package com.neuralnexusstudios.nexremote.core.network

import java.nio.charset.StandardCharsets
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

object CryptoUtils {
    private const val KEY_TEXT = "nexremote_encryption_key_32chars"
    private val keyBytes = ByteArray(32).also { bytes ->
        val source = KEY_TEXT.toByteArray(StandardCharsets.UTF_8)
        source.copyInto(bytes)
    }
    private val secretKey = SecretKeySpec(keyBytes, "AES")
    private val iv = IvParameterSpec(ByteArray(16))

    fun encryptToBase64(value: String): String {
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, iv)
        return Base64.getEncoder().encodeToString(cipher.doFinal(value.toByteArray(StandardCharsets.UTF_8)))
    }

    fun decryptBase64(value: String): String {
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(Cipher.DECRYPT_MODE, secretKey, iv)
        val bytes = Base64.getDecoder().decode(value)
        return cipher.doFinal(bytes).toString(StandardCharsets.UTF_8)
    }
}
