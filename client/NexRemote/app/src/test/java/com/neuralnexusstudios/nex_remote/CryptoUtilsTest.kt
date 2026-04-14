package com.neuralnexusstudios.nex_remote

import com.google.common.truth.Truth.assertThat
import com.neuralnexusstudios.nex_remote.core.model.DefaultGamepadLayouts
import com.neuralnexusstudios.nex_remote.core.network.CryptoUtils
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.Test

class CryptoUtilsTest {
    @Test
    fun encryptAndDecrypt_roundTrips() {
        val payload = """{"type":"mouse","action":"move_relative","dx":4,"dy":7}"""

        val encrypted = CryptoUtils.encryptToBase64(payload)
        val decrypted = CryptoUtils.decryptBase64(encrypted)

        assertThat(decrypted).isEqualTo(payload)
    }

    @Test
    fun builtInLayouts_serializeAndDeserialize() {
        val json = Json { ignoreUnknownKeys = true }
        val encoded = json.encodeToString(DefaultGamepadLayouts.builtIns)
        val decoded = json.decodeFromString<List<com.neuralnexusstudios.nex_remote.core.model.GamepadLayoutConfig>>(encoded)

        assertThat(decoded).hasSize(DefaultGamepadLayouts.builtIns.size)
        assertThat(decoded.first().id).isEqualTo("standard_gamepad")
    }
}
