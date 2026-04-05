package com.neuralnexusstudios.nexremote.core.network

import android.content.Context
import android.net.wifi.WifiManager
import com.neuralnexusstudios.nexremote.core.model.ServerInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.jsonObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

class DiscoveryRepository(context: Context) {
    private val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager

    fun isWifiEnabled(): Boolean = runCatching { wifiManager.isWifiEnabled }.getOrDefault(false)

    suspend fun discoverServers(timeoutMs: Int = 5_000): List<ServerInfo> = withContext(Dispatchers.IO) {
        if (!isWifiEnabled()) {
            return@withContext emptyList()
        }
        val lock = wifiManager.createMulticastLock("nexremote_discovery").apply { setReferenceCounted(false) }
        val servers = linkedMapOf<String, ServerInfo>()
        try {
            runCatching { lock.acquire() }.getOrElse { return@withContext emptyList() }
            DatagramSocket().use { socket ->
                socket.broadcast = true
                socket.soTimeout = timeoutMs
                val payload = "NEXREMOTE_DISCOVER".toByteArray()
                val request = DatagramPacket(
                    payload,
                    payload.size,
                    InetAddress.getByName("255.255.255.255"),
                    37020,
                )
                socket.send(request)

                val start = System.currentTimeMillis()
                while (System.currentTimeMillis() - start < timeoutMs) {
                    val buffer = ByteArray(4_096)
                    val response = DatagramPacket(buffer, buffer.size)
                    runCatching { socket.receive(response) }.onSuccess {
                        val text = response.data.copyOf(response.length).decodeToString()
                        val json = runCatching { JsonCodec.parseToJsonElement(text).jsonObject }.getOrNull() ?: return@onSuccess
                        if (json.string("type") == "discovery_response") {
                            val server = ServerInfo(
                                name = json.string("name") ?: "Unknown PC",
                                address = response.address.hostAddress ?: json.string("host").orEmpty(),
                                port = json.int("port") ?: 8765,
                                portInsecure = json.int("port_insecure") ?: 8766,
                                id = json.string("id").orEmpty(),
                                version = json.string("version") ?: "1.0.0",
                                certificateFingerprint = json.string("cert_fingerprint")
                                    ?: json.string("certificate_fingerprint")
                                    ?: json.string("certificate_thumbprint"),
                            )
                            servers[server.id.ifBlank { server.address }] = server
                        }
                    }.onFailure {
                        return@withContext servers.values.toList()
                    }
                }
            }
        } finally {
            runCatching { lock.release() }
        }
        servers.values.toList()
    }
}
