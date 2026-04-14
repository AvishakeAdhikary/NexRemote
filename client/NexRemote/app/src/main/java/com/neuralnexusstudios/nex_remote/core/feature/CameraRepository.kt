package com.neuralnexusstudios.nex_remote.core.feature

import com.neuralnexusstudios.nex_remote.core.model.CameraInfo
import com.neuralnexusstudios.nex_remote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nex_remote.core.network.int
import com.neuralnexusstudios.nex_remote.core.network.string
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
    private val _statusMessage = MutableStateFlow<String?>(null)

    val cameras: StateFlow<List<CameraInfo>> = _cameras
    val frames: StateFlow<Map<Int, ByteArray>> = _frames
    val activeCameras: StateFlow<Set<Int>> = _activeCameras
    val statusMessage: StateFlow<String?> = _statusMessage

    init {
        scope.launch {
            connectionRepository.messages.collect { payload ->
                if (payload.string("type") == "camera") {
                    when (payload.string("action")) {
                        "camera_list" -> {
                            _statusMessage.value = null
                            _cameras.value = payload["cameras"]?.jsonArray?.map { item ->
                                item.jsonObject.let {
                                    CameraInfo(
                                        index = it.int("index") ?: 0,
                                        name = it.string("name") ?: "Camera ${(it.int("index") ?: 0) + 1}",
                                    )
                                }
                            }.orEmpty()
                        }
                        "started" -> {
                            val index = payload.int("camera_index") ?: return@collect
                            _activeCameras.value = setOf(index)
                            _statusMessage.value = null
                        }
                        "multi_started" -> {
                            _activeCameras.value = payload["camera_indices"]?.jsonArray?.mapNotNull { it.jsonPrimitive.intOrNull }?.toSet().orEmpty()
                            _statusMessage.value = null
                        }
                        "stopped" -> {
                            val index = payload.int("camera_index") ?: return@collect
                            _activeCameras.update { it - index }
                            _frames.update { it - index }
                            _statusMessage.value = "Camera ${index + 1} stopped."
                        }
                        "stopped_all" -> {
                            _activeCameras.value = emptySet()
                            _frames.value = emptyMap()
                            _statusMessage.value = "Camera streaming stopped."
                        }
                        "error", "permission_required" -> {
                            val index = payload.int("camera_index")
                            if (index != null) {
                                _activeCameras.update { it - index }
                                _frames.update { it - index }
                            } else {
                                _frames.value = emptyMap()
                                _activeCameras.value = emptySet()
                            }
                            _statusMessage.value = payload.cameraStatusMessage()
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

    fun requestCameras() {
        _statusMessage.value = null
        connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "list_cameras"))
    }

    fun start(selected: Set<Int>) {
        _statusMessage.value = null
        _frames.update { current -> current.filterKeys { it in selected } }
        if (selected.size <= 1) {
            connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "start", "camera_index" to (selected.firstOrNull() ?: 0)))
        } else {
            connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "start_multi", "camera_indices" to selected.toList()))
        }
    }

    fun stop() {
        _activeCameras.value = emptySet()
        _frames.value = emptyMap()
        _statusMessage.value = "Camera streaming stopped."
        connectionRepository.sendMessage(mapOf("type" to "camera", "action" to "stop_all"))
    }

    private fun kotlinx.serialization.json.JsonObject.cameraStatusMessage(): String {
        string("message")?.let { return it }
        return when (string("code")) {
            "device_missing" -> "The selected webcam is no longer available on the PC."
            "access_denied" -> "Windows denied webcam access on the PC host."
            "initialize_failed" -> "The PC host could not initialize that webcam."
            "reader_start_failed" -> "The PC host could not start live frame capture for that webcam."
            "frame_timeout" -> "The webcam stopped producing live frames."
            "device_lost" -> "The webcam disconnected or stopped responding."
            "frame_encode_failed" -> "The PC host captured the webcam but could not encode the frames."
            else -> if (string("permission") == "camera") {
                "Camera access still needs approval on the PC host."
            } else {
                "Camera streaming failed."
            }
        }
    }
}
