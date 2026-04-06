package com.neuralnexusstudios.nexremote.core.network

import android.content.Context
import com.neuralnexusstudios.nexremote.BuildConfig
import com.neuralnexusstudios.nexremote.core.model.ConnectionStatus
import com.neuralnexusstudios.nexremote.core.model.FeatureStatus
import com.neuralnexusstudios.nexremote.core.model.ServerInfo
import com.neuralnexusstudios.nexremote.core.model.ServerCapabilities
import com.neuralnexusstudios.nexremote.core.model.ServerSessionState
import com.neuralnexusstudios.nexremote.core.storage.ClientIdentityStore
import com.neuralnexusstudios.nexremote.core.storage.AppPreferences
import com.neuralnexusstudios.nexremote.core.storage.CertificateStore
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeout
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.decodeFromJsonElement
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

class NexRemoteConnectionRepository(
    context: Context,
    private val preferences: AppPreferences,
    private val certificateStore: CertificateStore,
    private val clientIdentityStore: ClientIdentityStore,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val mutex = Mutex()

    private val baseClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private val permissiveTrustManager = object : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) = Unit
        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) = Unit
        override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }

    private val secureClient: OkHttpClient by lazy {
        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, arrayOf<TrustManager>(permissiveTrustManager), SecureRandom())
        baseClient.newBuilder()
            .sslSocketFactory(sslContext.socketFactory, permissiveTrustManager)
            .hostnameVerifier(HostnameVerifier { _, _ -> true })
            .build()
    }

    private var webSocket: WebSocket? = null
    private var pingJob: Job? = null
    private var reconnectJob: Job? = null
    private var realtimeJob: Job? = null
    private val pendingRealtime = ConcurrentHashMap<String, JsonObject>()

    private var intentionalDisconnect = false
    private var reconnectAttempt = 0
    private var missedPongs = 0

    private var lastHost: String? = null
    private var lastSecurePort: Int? = null
    private var lastInsecurePort: Int? = null
    private var lastTrySecureFirst: Boolean = true
    private var lastExpectedCertificateFingerprint: String? = null
    private var deviceId: String = ""
    private var deviceName: String = ""

    private val _connectionState = MutableStateFlow(ConnectionStatus.DISCONNECTED)
    private val _connectedDeviceName = MutableStateFlow("")
    private val _serverSessionState = MutableStateFlow(ServerSessionState())
    private val _messages = MutableSharedFlow<JsonObject>(extraBufferCapacity = 64)
    private val _binaryFrames = MutableSharedFlow<ByteArray>(extraBufferCapacity = 64)
    private val _events = MutableSharedFlow<String>(extraBufferCapacity = 16)

    val connectionState: StateFlow<ConnectionStatus> = _connectionState
    val connectedDeviceName: StateFlow<String> = _connectedDeviceName
    val serverSessionState: StateFlow<ServerSessionState> = _serverSessionState
    val messages: SharedFlow<JsonObject> = _messages
    val binaryFrames: SharedFlow<ByteArray> = _binaryFrames
    val events: SharedFlow<String> = _events

    init {
        startRealtimeLoop()
    }

    suspend fun connect(server: ServerInfo, trySecureFirst: Boolean = true): Boolean {
        val settings = preferences.settings.value
        return connect(
            host = server.address,
            securePort = server.port,
            insecurePort = server.portInsecure,
            deviceId = settings.deviceId,
            deviceName = settings.deviceName,
            expectedCertificateFingerprint = server.certificateFingerprint,
            trySecureFirst = trySecureFirst,
        )
    }

    suspend fun connect(
        host: String,
        securePort: Int,
        insecurePort: Int,
        deviceId: String,
        deviceName: String,
        expectedCertificateFingerprint: String? = null,
        trySecureFirst: Boolean = true,
    ): Boolean = mutex.withLock {
        intentionalDisconnect = false
        reconnectAttempt = 0
        lastHost = host
        lastSecurePort = securePort
        lastInsecurePort = insecurePort
        lastTrySecureFirst = trySecureFirst && preferences.settings.value.useSecureConnection
        lastExpectedCertificateFingerprint = expectedCertificateFingerprint
        this.deviceId = deviceId
        this.deviceName = deviceName
        preferences.updateLastServer("$host:$securePort")

        if (lastTrySecureFirst) {
            when (attemptConnection(host, securePort, secure = true, expectedCertificateFingerprint = expectedCertificateFingerprint)) {
                AttemptResult.Success -> return true
                AttemptResult.CertificateRejected -> return false
                AttemptResult.Failure -> Unit
            }
        }
        return attemptConnection(host, insecurePort, secure = false, expectedCertificateFingerprint = null) == AttemptResult.Success
    }

    suspend fun connectUsb(port: Int = 8766): Boolean {
        val settings = preferences.settings.value
        val success = connect(
            host = "127.0.0.1",
            securePort = port,
            insecurePort = port,
            deviceId = settings.deviceId,
            deviceName = settings.deviceName,
            trySecureFirst = false,
        )
        if (success) {
            lastSecurePort = null
            lastInsecurePort = port
            lastTrySecureFirst = false
        }
        return success
    }

    fun disconnect() {
        intentionalDisconnect = true
        reconnectJob?.cancel()
        pingJob?.cancel()
        pendingRealtime.clear()
        webSocket?.close(1000, "User disconnected")
        webSocket = null
        _connectionState.value = ConnectionStatus.DISCONNECTED
        _connectedDeviceName.value = ""
        _serverSessionState.value = ServerSessionState()
    }

    fun sendMessage(payload: Map<String, Any?>) {
        if (_connectionState.value != ConnectionStatus.CONNECTED) return
        val objectPayload = mapToJsonObject(payload)
        val realtimeKey = realtimeKeyFor(objectPayload)
        if (realtimeKey != null) {
            enqueueRealtime(realtimeKey, objectPayload)
            return
        }
        sendEncryptedJson(objectPayload)
    }

    fun sendRawJson(payload: Map<String, Any?>) {
        val json = JsonCodec.encodeToString(JsonObject.serializer(), mapToJsonObject(payload))
        webSocket?.send(json)
    }

    private fun sendEncryptedJson(payload: JsonObject) {
        val json = JsonCodec.encodeToString(JsonObject.serializer(), payload)
        webSocket?.send(CryptoUtils.encryptToBase64(json))
    }

    private suspend fun attemptConnection(
        host: String,
        port: Int,
        secure: Boolean,
        expectedCertificateFingerprint: String? = null,
    ): AttemptResult {
        val authResult = CompletableDeferred<AttemptResult>()
        val authState = AuthHandshakeState(secure = secure)
        val wsUrl = "${if (secure) "wss" else "ws"}://$host:$port"
        _connectionState.value = ConnectionStatus.CONNECTING

        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                if (secure) {
                    val certificate = response.handshake?.peerCertificates?.firstOrNull()
                    if (certificate != null && !certificateStore.trustOrVerify(host, certificate, expectedCertificateFingerprint)) {
                        authResult.complete(AttemptResult.CertificateRejected)
                        webSocket.close(1008, "Certificate mismatch")
                        return
                    }
                }

                this@NexRemoteConnectionRepository.webSocket = webSocket
                sendRawJson(
                    mapOf(
                        "type" to "auth",
                        "device_id" to deviceId,
                        "device_name" to deviceName,
                        "client_public_key" to clientIdentityStore.publicKeyBase64,
                        "client_version" to BuildConfig.VERSION_NAME,
                        "platform" to "android",
                    ),
                )
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleIncomingText(text, authResult, authState)
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                _binaryFrames.tryEmit(bytes.toByteArray())
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                if (!authResult.isCompleted) {
                    authResult.complete(AttemptResult.Failure)
                } else {
                    handleSocketFailure()
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                if (!authResult.isCompleted) {
                    authResult.complete(AttemptResult.Failure)
                } else {
                    handleSocketFailure()
                }
            }
        }

        val request = Request.Builder().url(wsUrl).build()
        val client = if (secure) secureClient else baseClient
        client.newWebSocket(request, listener)

        return try {
            when (withTimeout(15_000) { authResult.await() }) {
                AttemptResult.Success -> {
                    reconnectAttempt = 0
                    startPingLoop()
                    AttemptResult.Success
                }
                AttemptResult.CertificateRejected -> {
                    _events.tryEmit("The trusted certificate for $host changed. Secure connection was rejected.")
                    webSocket?.close(1000, "Certificate rejected")
                    webSocket = null
                    _connectionState.value = ConnectionStatus.DISCONNECTED
                    AttemptResult.CertificateRejected
                }
                AttemptResult.Failure -> {
                    webSocket?.close(1000, "Connect failed")
                    webSocket = null
                    _connectionState.value = ConnectionStatus.DISCONNECTED
                    AttemptResult.Failure
                }
            }
        } catch (_: Throwable) {
            webSocket?.close(1000, "Connect timeout")
            webSocket = null
            _connectionState.value = ConnectionStatus.DISCONNECTED
            AttemptResult.Failure
        }
    }

    private fun handleIncomingText(
        text: String,
        authResult: CompletableDeferred<AttemptResult>,
        authState: AuthHandshakeState,
    ) {
        val plainJson = runCatching { JsonCodec.parseToJsonElement(text).jsonObject }.getOrNull()
        val decoded = plainJson ?: runCatching {
            JsonCodec.parseToJsonElement(CryptoUtils.decryptBase64(text)).jsonObject
        }.getOrNull()
        val payload = decoded ?: return
        when (payload.string("type")) {
            "auth_challenge" -> {
                val nonce = decodeNonce(payload)
                if (nonce == null) {
                    _events.tryEmit("The server sent an invalid auth challenge.")
                    webSocket?.close(1008, "Invalid challenge")
                    authResult.complete(AttemptResult.Failure)
                    return
                }

                authState.challengeSeen = true
                authState.challengeNonce = nonce
                updateServerSessionState(payload, connected = false)
                val signature = runCatching { clientIdentityStore.signNonce(nonce) }.getOrNull()
                if (signature == null) {
                    _events.tryEmit("Unable to sign the server challenge for secure pairing.")
                    webSocket?.close(1011, "Signing failed")
                    authResult.complete(AttemptResult.Failure)
                    return
                }
                sendRawJson(
                    mapOf(
                        "type" to "auth_response",
                        "device_id" to deviceId,
                        "signature" to signature,
                    ),
                )
            }
            "auth_success" -> {
                if (authState.secure && !authState.challengeSeen) {
                    _events.tryEmit("Secure pairing requires a server challenge before accepting auth success.")
                    webSocket?.close(1008, "Challenge required")
                    authResult.complete(AttemptResult.Failure)
                    return
                }
                _connectionState.value = ConnectionStatus.CONNECTED
                _connectedDeviceName.value = payload.string("server_name") ?: payload.string("name").orEmpty()
                updateServerSessionState(payload, connected = true)
                _messages.tryEmit(payload)
                authResult.complete(AttemptResult.Success)
            }
            "feature_status", "server_status" -> {
                _serverSessionState.value = _serverSessionState.value.copy(
                    connected = _connectionState.value == ConnectionStatus.CONNECTED,
                    featureStatus = extractFeatureStatus(payload),
                )
                _messages.tryEmit(payload)
            }
            "auth_failed", "connection_rejected" -> {
                _messages.tryEmit(payload)
                authResult.complete(AttemptResult.Failure)
            }
            "pong" -> missedPongs = 0
            else -> _messages.tryEmit(payload)
        }
    }

    private fun handleSocketFailure() {
        pingJob?.cancel()
        pendingRealtime.clear()
        webSocket = null
        if (!intentionalDisconnect) {
            _connectionState.value = ConnectionStatus.CONNECTING
            scheduleReconnect()
        } else {
            _connectionState.value = ConnectionStatus.DISCONNECTED
            _serverSessionState.value = ServerSessionState()
        }
    }

    private fun startRealtimeLoop() {
        realtimeJob?.cancel()
        realtimeJob = scope.launch {
            while (true) {
                delay(6)
                if (_connectionState.value != ConnectionStatus.CONNECTED || pendingRealtime.isEmpty()) {
                    continue
                }

                val snapshot = pendingRealtime.entries.toList()
                snapshot.forEach { (key, payload) ->
                    if (pendingRealtime.remove(key, payload)) {
                        sendEncryptedJson(payload)
                    }
                }
            }
        }
    }

    private fun enqueueRealtime(key: String, payload: JsonObject) {
        val type = payload.string("type").orEmpty()
        val action = payload.string("action").orEmpty()
        val merged = when {
            type == "mouse" && action == "move_relative" -> mergeDeltaPayload(key, payload)
            type == "mouse" && action == "scroll" -> mergeDeltaPayload(key, payload)
            else -> payload
        }
        pendingRealtime[key] = merged
    }

    private fun mergeDeltaPayload(key: String, payload: JsonObject): JsonObject {
        val existing = pendingRealtime[key] ?: return payload
        val dx = (existing.int("dx") ?: 0) + (payload.int("dx") ?: 0)
        val dy = (existing.int("dy") ?: 0) + (payload.int("dy") ?: 0)
        return JsonObject(payload.toMutableMap().apply {
            this["dx"] = kotlinx.serialization.json.JsonPrimitive(dx)
            this["dy"] = kotlinx.serialization.json.JsonPrimitive(dy)
        })
    }

    private fun realtimeKeyFor(payload: JsonObject): String? {
        return when (payload.string("type")) {
            "mouse" -> when (payload.string("action")) {
                "move_relative" -> "mouse_move_relative"
                "scroll" -> "mouse_scroll"
                else -> null
            }
            "gamepad", "gamepad_dinput", "gamepad_android" -> when (payload.string("input_type")) {
                "joystick" -> "gamepad_joystick_${payload.string("stick").orEmpty()}"
                "trigger" -> "gamepad_trigger_${payload.string("trigger").orEmpty()}"
                "gyro" -> "gamepad_gyro"
                else -> null
            }
            else -> null
        }
    }

    private fun startPingLoop() {
        pingJob?.cancel()
        missedPongs = 0
        pingJob = scope.launch {
            while (true) {
                delay(15_000)
                if (_connectionState.value != ConnectionStatus.CONNECTED) continue
                missedPongs += 1
                if (missedPongs > 3) {
                    handleSocketFailure()
                    break
                }
                sendRawJson(mapOf("type" to "ping"))
            }
        }
    }

    private fun scheduleReconnect() {
        if (reconnectJob?.isActive == true || intentionalDisconnect) return
        val host = lastHost ?: return
        reconnectJob = scope.launch {
            while (!intentionalDisconnect && reconnectAttempt < 15) {
                val delaySeconds = (1 shl reconnectAttempt).coerceAtMost(30)
                reconnectAttempt += 1
                delay(delaySeconds * 1_000L)
                val success = connect(
                    host = host,
                    securePort = lastSecurePort ?: 8765,
                    insecurePort = lastInsecurePort ?: 8766,
                    deviceId = deviceId,
                    deviceName = deviceName,
                    expectedCertificateFingerprint = lastExpectedCertificateFingerprint,
                    trySecureFirst = lastTrySecureFirst,
                )
                if (success) break
            }
            if (!intentionalDisconnect && _connectionState.value != ConnectionStatus.CONNECTED) {
                _connectionState.value = ConnectionStatus.DISCONNECTED
                _events.tryEmit("Unable to reconnect to the PC server.")
            }
        }
    }

    private enum class AttemptResult {
        Success,
        Failure,
        CertificateRejected,
    }

    private data class AuthHandshakeState(
        val secure: Boolean,
        var challengeSeen: Boolean = false,
        var challengeNonce: ByteArray? = null,
    )

    private fun parseFeatureStatusMap(objectValue: JsonObject?): Map<String, FeatureStatus> {
        if (objectValue == null) return emptyMap()
        return objectValue.mapValues { (_, value) ->
            runCatching { JsonCodec.decodeFromJsonElement<FeatureStatus>(value) }.getOrDefault(FeatureStatus())
        }
    }

    private fun updateServerSessionState(payload: JsonObject, connected: Boolean) {
        _serverSessionState.value = ServerSessionState(
            serverName = payload.string("server_name") ?: payload.string("name").orEmpty(),
            connected = connected,
            capabilities = payload["capabilities"]?.let { runCatching { JsonCodec.decodeFromJsonElement<ServerCapabilities>(it) }.getOrNull() },
            featureStatus = extractFeatureStatus(payload),
        )
    }

    private fun extractFeatureStatus(payload: JsonObject): Map<String, FeatureStatus> {
        payload["feature_status"]?.jsonObject?.let { return parseFeatureStatusMap(it) }
        val reservedKeys = setOf("type", "server_name", "name", "capabilities", "feature_status")
        val featureObject = payload.filterKeys { it !in reservedKeys }
        return if (featureObject.isEmpty()) emptyMap() else parseFeatureStatusMap(JsonObject(featureObject))
    }

    private fun decodeNonce(payload: JsonObject): ByteArray? {
        payload.string("nonce")?.let { value ->
            return runCatching { java.util.Base64.getDecoder().decode(value) }
                .getOrElse { runCatching { hexToBytes(value) }.getOrNull() }
        }

        val bytes = payload["nonce"]?.jsonArray?.mapNotNull { it.jsonPrimitive.intOrNull?.toByte() }
        return bytes?.takeIf { it.isNotEmpty() }?.toByteArray()
    }

    private fun hexToBytes(value: String): ByteArray {
        val cleaned = value.replace(" ", "").replace(":", "")
        require(cleaned.length % 2 == 0) { "Invalid hex nonce" }
        return ByteArray(cleaned.length / 2) { index ->
            cleaned.substring(index * 2, index * 2 + 2).toInt(16).toByte()
        }
    }
}
