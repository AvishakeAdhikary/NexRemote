package com.neuralnexusstudios.nexremote.core.feature

import android.os.SystemClock
import com.neuralnexusstudios.nexremote.core.model.DisplayInfo
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nexremote.core.network.bool
import com.neuralnexusstudios.nexremote.core.network.int
import com.neuralnexusstudios.nexremote.core.network.string
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.util.concurrent.ConcurrentHashMap

class ScreenShareRepository(private val connectionRepository: NexRemoteConnectionRepository) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _displays = MutableStateFlow<List<DisplayInfo>>(emptyList())
    private val _frames = MutableStateFlow<Map<Int, ByteArray>>(emptyMap())
    private val _activeDisplays = MutableStateFlow<List<Int>>(emptyList())
    private val _fps = MutableStateFlow(30)
    private val _quality = MutableStateFlow(70)
    private val _resolution = MutableStateFlow("native")
    private val displayGeometry = ConcurrentHashMap<Int, DisplayInfo>()
    private var lastMoveSentAtMs = 0L

    val displays: StateFlow<List<DisplayInfo>> = _displays
    val frames: StateFlow<Map<Int, ByteArray>> = _frames
    val activeDisplays: StateFlow<List<Int>> = _activeDisplays
    val currentFps: StateFlow<Int> = _fps
    val currentQuality: StateFlow<Int> = _quality
    val currentResolution: StateFlow<String> = _resolution

    init {
        scope.launch {
            connectionRepository.messages.collect { payload ->
                if (payload.string("type") == "screen_share" && payload.string("action") == "display_list") {
                    val displays = payload["displays"]?.jsonArray?.map { item ->
                        item.jsonObject.let {
                            DisplayInfo(
                                index = it.int("index") ?: 0,
                                    name = it.string("name") ?: "Display",
                                    width = it.int("width") ?: 1920,
                                    height = it.int("height") ?: 1080,
                                    left = it.int("left") ?: it.int("x") ?: 0,
                                    top = it.int("top") ?: it.int("y") ?: 0,
                                    isPrimary = it.bool("is_primary") ?: false,
                            )
                        }
                    }.orEmpty()
                    displayGeometry.clear()
                    displays.forEach { displayGeometry[it.index] = it }
                    _displays.value = displays
                    _activeDisplays.value = payload["active_displays"]?.jsonArray?.mapNotNull { it.jsonPrimitive.intOrNull }.orEmpty()
                    _fps.value = payload.int("current_fps") ?: _fps.value
                    _quality.value = payload.int("current_quality") ?: _quality.value
                    _resolution.value = payload.string("current_resolution") ?: _resolution.value
                }
            }
        }
        scope.launch {
            connectionRepository.binaryFrames.collect { bytes ->
                if (bytes.size > 5 && bytes[0] == 0x53.toByte() && bytes[1] == 0x43.toByte() && bytes[2] == 0x52.toByte() && bytes[3] == 0x4E.toByte()) {
                    val index = bytes[4].toInt()
                    _frames.update { it + (index to bytes.copyOfRange(5, bytes.size)) }
                }
            }
        }
    }

    fun requestDisplays() = connectionRepository.sendMessage(mapOf("type" to "screen_share", "action" to "list_displays"))

    fun start(displayIndices: List<Int>, fps: Int, qualityLabel: String, resolution: String) {
        val quality = when (qualityLabel) {
            "low" -> 30
            "medium" -> 50
            "high" -> 70
            "ultra" -> 90
            else -> 50
        }
        _activeDisplays.value = displayIndices
        _fps.value = fps
        _quality.value = quality
        _resolution.value = resolution
        connectionRepository.sendMessage(
            mapOf(
                "type" to "screen_share",
                "action" to "start",
                "display_index" to (displayIndices.firstOrNull() ?: 0),
                "display_indices" to displayIndices,
                "fps" to fps,
                "quality" to quality,
                "resolution" to resolution,
            ),
        )
    }

    fun stop() {
        _activeDisplays.value = emptyList()
        connectionRepository.sendMessage(mapOf("type" to "screen_share", "action" to "stop"))
    }

    fun setFps(fps: Int) {
        _fps.value = fps
        connectionRepository.sendMessage(mapOf("type" to "screen_share", "action" to "set_fps", "fps" to fps))
    }

    fun setQuality(quality: Int) {
        _quality.value = quality
        connectionRepository.sendMessage(mapOf("type" to "screen_share", "action" to "set_quality", "quality" to quality))
    }

    fun setResolution(resolution: String) {
        _resolution.value = resolution
        connectionRepository.sendMessage(mapOf("type" to "screen_share", "action" to "set_resolution", "resolution" to resolution))
    }

    fun sendInput(
        monitorIndex: Int,
        action: String,
        normalizedX: Float,
        normalizedY: Float,
        extras: Map<String, Any?> = emptyMap(),
    ) {
        if (action == "move") {
            val now = SystemClock.elapsedRealtime()
            if (now - lastMoveSentAtMs < 16L) {
                return
            }
            lastMoveSentAtMs = now
        }

        val display = displayGeometry[monitorIndex]
        val width = display?.width?.coerceAtLeast(1) ?: 1920
        val height = display?.height?.coerceAtLeast(1) ?: 1080
        val localX = (normalizedX.coerceIn(0f, 1f) * width).toInt()
        val localY = (normalizedY.coerceIn(0f, 1f) * height).toInt()
        val absoluteX = (display?.left ?: 0) + localX
        val absoluteY = (display?.top ?: 0) + localY

        connectionRepository.sendMessage(
            mapOf(
                "type" to "screen_share",
                "action" to "input",
                "monitor_index" to monitorIndex,
                "input_action" to action,
                "normalized_x" to normalizedX.coerceIn(0f, 1f),
                "normalized_y" to normalizedY.coerceIn(0f, 1f),
                "monitor_x" to localX,
                "monitor_y" to localY,
                "x" to absoluteX,
                "y" to absoluteY,
            ) + extras,
        )
    }
}
