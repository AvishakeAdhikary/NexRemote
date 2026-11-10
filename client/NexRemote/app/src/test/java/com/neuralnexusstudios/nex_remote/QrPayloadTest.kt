package com.neuralnexusstudios.nex_remote

import com.google.common.truth.Truth.assertThat
import com.neuralnexusstudios.nex_remote.ui.screens.parseQrPayload
import org.junit.Test

class QrPayloadTest {
    @Test
    fun parsesHostQrPayload() {
        val server = parseQrPayload(
            """{"host":"192.168.0.240","port":8765,"port_insecure":8766,"name":"My PC","id":"abc","cert_fingerprint":"AA:BB"}""",
        )
        assertThat(server).isNotNull()
        assertThat(server!!.address).isEqualTo("192.168.0.240")
        assertThat(server.port).isEqualTo(8765)
        assertThat(server.portInsecure).isEqualTo(8766)
        assertThat(server.name).isEqualTo("My PC")
        assertThat(server.certificateFingerprint).isEqualTo("AA:BB")
    }

    @Test
    fun defaultsMissingPortsAndName() {
        val server = parseQrPayload("""{"host":"10.0.0.5"}""")!!
        assertThat(server.port).isEqualTo(8765)
        assertThat(server.portInsecure).isEqualTo(8766)
        assertThat(server.name).isEqualTo("PC")
    }

    @Test
    fun rejectsCodesThatAreNotFromNexRemote() {
        assertThat(parseQrPayload("https://example.com")).isNull()
        assertThat(parseQrPayload("""{"name":"no host"}""")).isNull()
        assertThat(parseQrPayload("")).isNull()
    }
}
