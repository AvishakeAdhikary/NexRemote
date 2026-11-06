package com.neuralnexusstudios.nex_remote.core.feature

import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat
import com.neuralnexusstudios.nex_remote.core.model.ConnectionStatus
import com.neuralnexusstudios.nex_remote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nex_remote.core.network.string
import com.neuralnexusstudios.nex_remote.core.storage.AppPreferences
import com.neuralnexusstudios.nex_remote.service.NexRemoteControlService
import com.neuralnexusstudios.nex_remote.service.PhoneAudioCapture
import com.neuralnexusstudios.nex_remote.service.ScreenCastService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch
import java.nio.ByteBuffer

/**
 * Phone → PC screen sharing and PC → phone remote control.
 *
 * Wire contract (root AGENTS.md): `phone_screen` start/config_changed/control_changed/stop
 * messages, and PSCR binary frames = "PSCR" | index | flags | pts µs (i64 BE) | H.264 Annex B.
 * The host sends `input`, `request_keyframe` and `stop_request`. Input is acted on only while
 * sharing, with "Allow PC control" on and the accessibility service enabled by the user.
 *
 * 1.2: the host may send `audio_request {enabled}`. Audio starts only when the user turned on "Let the
 * PC hear this phone" (and granted the permission Android requires); the phone replies with
 * `audio_changed {audio_active, sample_rate, channels}` and streams PAUD frames =
 * "PAUD" | index | pts µs (i64 BE) | PCM16 LE interleaved.
 */
class PhoneScreenRepository(
    private val context: Context,
    private val preferences: AppPreferences,
    private val connectionRepository: NexRemoteConnectionRepository,
) {
    enum class Status { Idle, Starting, Sharing }

    data class UiState(
        val status: Status = Status.Idle,
        val width: Int = 0,
        val height: Int = 0,
        val message: String? = null,
    )

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state

    /** Whether the PC may currently control this phone (all three conditions hold). */
    val controlActive: Boolean
        get() = _state.value.status == Status.Sharing &&
            preferences.settings.value.allowPcControl &&
            NexRemoteControlService.isRunning

    private var lastFormat: Format? = null

    private data class Format(val width: Int, val height: Int, val fps: Int, val rotation: Int)

    init {
        scope.launch {
            connectionRepository.messages.collect { message ->
                if (message.string("type") != "phone_screen") return@collect
                when (message.string("action")) {
                    "input" -> if (controlActive) NexRemoteControlService.instance?.perform(message)
                    "request_keyframe" -> ScreenCastService.requestKeyframe()
                    "stop_request" -> stop()
                    "audio_request" -> onAudioRequest(message["enabled"]?.toString() == "true")
                }
            }
        }
        scope.launch {
            connectionRepository.connectionState.collect { status ->
                if (status != ConnectionStatus.CONNECTED && _state.value.status != Status.Idle) {
                    stopService("The connection to the PC was lost, so screen sharing stopped.")
                }
            }
        }
        // Tell the host whenever audio becomes (un)available, and stop audio if the user turns it off.
        scope.launch {
            preferences.settings.collect { settings ->
                val available = audioAvailable()
                if (_state.value.status == Status.Sharing && available != lastAudioAvailable) {
                    lastAudioAvailable = available
                    if (!available) setAudioActive(false)
                    sendAudioChanged()
                }
                if (!settings.allowPcAudio && audioActive) setAudioActive(false)
            }
        }
        // Tell the host whenever the effective control permission changes.
        scope.launch {
            combine(preferences.settings, NexRemoteControlService.running) { settings, running ->
                settings.allowPcControl && running
            }.distinctUntilChanged().collect { allowed ->
                if (_state.value.status == Status.Sharing) {
                    connectionRepository.sendMessage(
                        mapOf("type" to "phone_screen", "action" to "control_changed", "control_available" to allowed),
                    )
                }
            }
        }
    }

    fun hostSupportsPhoneScreen(): Boolean =
        connectionRepository.serverSessionState.value.capabilities?.phoneScreen == true

    /** Starts the capture service with the user's MediaProjection consent result. */
    fun start(resultCode: Int, consent: Intent) {
        _state.value = UiState(status = Status.Starting)
        val intent = Intent(context, ScreenCastService::class.java)
            .setAction(ScreenCastService.ACTION_START)
            .putExtra(ScreenCastService.EXTRA_RESULT_CODE, resultCode)
            .putExtra(ScreenCastService.EXTRA_RESULT_DATA, consent)
        ContextCompat.startForegroundService(context, intent)
    }

    fun stop() {
        if (_state.value.status != Status.Idle) {
            connectionRepository.sendMessage(mapOf("type" to "phone_screen", "action" to "stop"))
        }
        stopService(null)
    }

    private fun stopService(message: String?) {
        context.startService(Intent(context, ScreenCastService::class.java).setAction(ScreenCastService.ACTION_STOP))
        lastFormat = null
        _state.value = UiState(status = Status.Idle, message = message)
    }

    fun setAllowPcControl(enabled: Boolean) = preferences.updateAllowPcControl(enabled)

    fun setAllowPcAudio(enabled: Boolean) = preferences.updateAllowPcAudio(enabled)

    // ---- audio (1.2) ---------------------------------------------------------------------------
    @Volatile private var audioActive = false
    private var lastAudioAvailable = false

    /** The user allowed it, Android 10+, and the permission Android requires is granted. */
    fun audioAvailable(): Boolean =
        preferences.settings.value.allowPcAudio && PhoneAudioCapture.canCapture(context)

    private fun onAudioRequest(enabled: Boolean) {
        if (_state.value.status != Status.Sharing) return
        setAudioActive(enabled && audioAvailable())
        sendAudioChanged()
    }

    private fun setAudioActive(enabled: Boolean) {
        audioActive = ScreenCastService.setAudio(enabled)
    }

    private fun sendAudioChanged() {
        connectionRepository.sendMessage(
            mapOf(
                "type" to "phone_screen",
                "action" to "audio_changed",
                "audio_active" to audioActive,
                "audio_available" to audioAvailable(),
                "sample_rate" to PhoneAudioCapture.SAMPLE_RATE,
                "channels" to PhoneAudioCapture.CHANNELS,
            ),
        )
    }

    internal fun onAudioChunk(ptsUs: Long, pcm: ByteArray) {
        if (!audioActive) return
        connectionRepository.sendBinary(buildAudioFrame(ptsUs, pcm), droppable = true)
    }

    // Called by ScreenCastService -------------------------------------------------------------

    internal fun onEncoderStarted(width: Int, height: Int, fps: Int, rotation: Int) {
        val format = Format(width, height, fps, rotation)
        val action = if (lastFormat == null) "start" else "config_changed"
        lastFormat = format
        connectionRepository.sendMessage(
            mapOf(
                "type" to "phone_screen",
                "action" to action,
                "codec" to "h264",
                "width" to width,
                "height" to height,
                "fps" to fps,
                "rotation" to rotation,
                "control_available" to (preferences.settings.value.allowPcControl && NexRemoteControlService.isRunning),
                "audio_available" to audioAvailable(),
            ),
        )
        if (action == "start") {
            audioActive = false
            lastAudioAvailable = audioAvailable()
        }
        _state.value = UiState(status = Status.Sharing, width = width, height = height)
    }

    internal fun onEncodedFrame(flags: Int, ptsUs: Long, data: ByteArray): Boolean =
        connectionRepository.sendBinary(
            buildFrame(flags, ptsUs, data),
            droppable = flags == 0, // never drop codec config or keyframes
        )

    internal fun onCaptureStopped(message: String?) {
        audioActive = false
        if (_state.value.status != Status.Idle) {
            connectionRepository.sendMessage(mapOf("type" to "phone_screen", "action" to "stop"))
        }
        lastFormat = null
        _state.value = UiState(status = Status.Idle, message = message)
    }

    companion object {
        const val FLAG_CONFIG = 0x01
        const val FLAG_KEYFRAME = 0x02
        private val TAG = byteArrayOf('P'.code.toByte(), 'S'.code.toByte(), 'C'.code.toByte(), 'R'.code.toByte())
        private val AUDIO_TAG = byteArrayOf('P'.code.toByte(), 'A'.code.toByte(), 'U'.code.toByte(), 'D'.code.toByte())

        /** "PAUD" | index 0 | pts (i64 BE) | PCM16 LE interleaved */
        fun buildAudioFrame(ptsUs: Long, pcm: ByteArray, index: Int = 0): ByteArray =
            ByteBuffer.allocate(4 + 1 + 8 + pcm.size)
                .put(AUDIO_TAG)
                .put(index.toByte())
                .putLong(ptsUs)
                .put(pcm)
                .array()

        /** "PSCR" | index 0 | flags | pts (i64 BE) | data */
        fun buildFrame(flags: Int, ptsUs: Long, data: ByteArray, index: Int = 0): ByteArray =
            ByteBuffer.allocate(4 + 1 + 1 + 8 + data.size)
                .put(TAG)
                .put(index.toByte())
                .put(flags.toByte())
                .putLong(ptsUs)
                .put(data)
                .array()
    }
}
