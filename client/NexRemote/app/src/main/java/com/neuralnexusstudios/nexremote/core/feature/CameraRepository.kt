package com.neuralnexusstudios.nexremote.core.feature

import com.neuralnexusstudios.nexremote.core.model.CameraInfo
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
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

class CameraRepository(private val connectionRepository: NexRemoteConnectionRepository) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _cameras = MutableStateFlow<List<CameraInfo>>(emptyList())
    private val _frames = MutableStateFlow<Map<Int, ByteArray>>(emptyMap())
    private val _activeCameras = MutableStateFlow<Set<Int>>(emptySet())

    val cameras: StateFlow<List<CameraInfo>> = _cameras
    val frames: StateFlow<Map<Int, ByteArray>> = _frames
    val activeCameras: StateFlow<Set<Int>> = _activeCameras

    init {
        scope.launch {
            connectionRepository.messages.collect { payload ->
                if (payload.string("type") == "camera") {
                    when (payload.string("action")) {
                        "camera_list" -> {
                            _cameras.value = payload["cameras"]?.jsonArray?.map { item ->
                                item.jsonObject.let {
                                    CameraInfo(
                                        index = it.int("index") ?: 0,
                                        name = it.string("name") ?: "Camera ${(it.int("index") ?: 0) + 1}",
                                    )
                                }
                            }.orEmpty()
                        }
                        "multi_started" -> {
                            _activeCameras.value = payload["camera_indices"]?.jsonArray?.mapNotNull { it.jsonPrimitive.intOrNull }?.toSet().orEmpty()
                        }
                    }
                }
            }
        }
        scope.launch {
            connectionRepository.binaryFrames.collect { bytes ->
                if (bytes.size > 5 && bytes[0] == 0x43.toByte() && bytes[1] == 0x41.toByte() && bytes[2] == 0x4D.toByte() && bytes[3] == 0x46.toByte()) {
                    val index = bytes[4].toInt()
                    _frames.update { it + (index to bytes.copyOfRange(5, bytes.size)) }
                }
            }
        }
    }

    fun requestCameras() = connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "list_cameras"))

    fun start(selected: Set<Int>) {
        _activeCameras.value = selected
        if (selected.size <= 1) {
            connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "start", "camera_index" to (selected.firstOrNull() ?: 0)))
        } else {
            connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "start_multi", "camera_indices" to selected.toList()))
        }
    }

    fun stop() {
        _activeCameras.value = emptySet()
        connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "stop_all"))
    }
}
