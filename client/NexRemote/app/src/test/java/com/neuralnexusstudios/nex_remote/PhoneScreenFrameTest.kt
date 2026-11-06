package com.neuralnexusstudios.nex_remote

import com.google.common.truth.Truth.assertThat
import com.neuralnexusstudios.nex_remote.core.feature.PhoneScreenRepository
import org.junit.Test

class PhoneScreenFrameTest {
    @Test
    fun buildFrame_matchesHostLayout() {
        // Same bytes the host test builds with build_phone_screen(0, CONFIG|KEYFRAME, 123456789, ...).
        val frame = PhoneScreenRepository.buildFrame(
            flags = PhoneScreenRepository.FLAG_CONFIG or PhoneScreenRepository.FLAG_KEYFRAME,
            ptsUs = 123_456_789L,
            data = byteArrayOf(0, 0, 0, 1, 0x67),
        )
        val expected = "PSCR".toByteArray() + byteArrayOf(0, 3) +
            byteArrayOf(0, 0, 0, 0, 0x07, 0x5B, 0xCD.toByte(), 0x15) + byteArrayOf(0, 0, 0, 1, 0x67)
        assertThat(frame).isEqualTo(expected)
    }
}

class PhoneAudioFrameTest {
    @org.junit.Test
    fun audioFrameLayoutMatchesWireContract() {
        val pcm = byteArrayOf(1, 0, 2, 0)
        val frame = com.neuralnexusstudios.nex_remote.core.feature.PhoneScreenRepository.buildAudioFrame(0x0102030405L, pcm)
        // "PAUD" | index 0 | pts i64 big-endian | PCM16 LE
        com.google.common.truth.Truth.assertThat(frame.copyOfRange(0, 4).decodeToString()).isEqualTo("PAUD")
        com.google.common.truth.Truth.assertThat(frame[4]).isEqualTo(0.toByte())
        com.google.common.truth.Truth.assertThat(frame.copyOfRange(5, 13).map { it.toInt() })
            .containsExactly(0, 0, 0, 1, 2, 3, 4, 5).inOrder()
        com.google.common.truth.Truth.assertThat(frame.copyOfRange(13, frame.size).toList()).isEqualTo(pcm.toList())
    }
}
