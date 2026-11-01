package com.neuralnexusstudios.nex_remote

import com.google.common.truth.Truth.assertThat
import com.neuralnexusstudios.nex_remote.core.network.SessionCipher
import com.neuralnexusstudios.nex_remote.core.network.SessionCrypto
import org.junit.Assert.assertThrows
import org.junit.Test
import java.math.BigInteger

/** Vectors come from the Python host (windows_app/server/tests) so both sides provably agree. */
class SessionCryptoTest {
    private fun hex(s: String) = ByteArray(s.length / 2) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }

    @Test
    fun hkdf_matchesRfc5869TestCase1() {
        val okm = SessionCrypto.hkdf(
            ikm = hex("0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b"),
            salt = hex("000102030405060708090a0b0c"),
            info = hex("f0f1f2f3f4f5f6f7f8f9"),
            length = 42,
        )
        assertThat(okm).isEqualTo(
            hex("3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"),
        )
    }

    @Test
    fun aesGcm_knownAnswerMatchesHost() {
        val cipher = SessionCipher(sendKey = ByteArray(32) { it.toByte() }, recvKey = ByteArray(32))
        assertThat(cipher.encrypt("""{"type":"ping"}""")).isEqualTo("dZ7Bp8VJoYcq2MBbfw7sx1qikhQ6HIzE88g+vhoMbA==")
        assertThat(cipher.encrypt("""{"type":"ping"}""")).isEqualTo("bvTLhTSREiQsXjhXi4RHFKIoKnBBg/O4xhf9XmnRqg==")
    }

    @Test
    fun keyDerivation_matchesHostVector() {
        val clientPrivate = SessionCrypto.privateKeyFromScalar(BigInteger("11".repeat(32), 16))
        val clientSpki = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEAhfmF/C2RDkoJ4+WmZ5pojpPLBUr321s32bluAKC1O0ZSn3ry5dxLS3aPKhaqHZaVvRfx1hZllLyiXxlMG5XlA=="
        val serverSpki = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE1lqTl3yqPRsIGFL/V6eeRl8WYFdzBLrq1QXdOkhYnPNQGF6JU3LfYiHqOhN1V+Rz/dtnVfBb1QfDxTP86ckShQ=="

        val (c2s, s2c) = SessionCrypto.deriveClientKeys(clientPrivate, clientSpki, serverSpki)

        assertThat(c2s).isEqualTo(hex("8e83de333d6bd71a4dc3cf1dcd61d201805f280e73015c752e7db94b15580a2d"))
        assertThat(s2c).isEqualTo(hex("83978349e3322cebbc952263f00c6f886a833097905efe522a5da8d8cd02da5c"))
        // First message the host sends on that session.
        val client = SessionCipher.forClient(c2s, s2c)
        assertThat(client.decrypt("aUBWnJs6id2vdOjiFPo3PwYG7EwGUE6qBo3vrKXJzw==")).isEqualTo("""{"type":"pong"}""")
    }

    @Test
    fun replayedMessageIsRejected() {
        val key = ByteArray(32) { 7 }
        val sender = SessionCipher(sendKey = key, recvKey = ByteArray(32))
        val receiver = SessionCipher(sendKey = ByteArray(32), recvKey = key)
        val first = sender.encrypt("one")
        assertThat(receiver.decrypt(first)).isEqualTo("one")
        assertThrows(Exception::class.java) { receiver.decrypt(first) }
    }
}
