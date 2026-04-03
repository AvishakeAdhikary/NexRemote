package com.neuralnexusstudios.nexremote.core.feature

import com.neuralnexusstudios.nexremote.core.model.MediaState
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nexremote.core.network.bool
import com.neuralnexusstudios.nexremote.core.network.int
import com.neuralnexusstudios.nexremote.core.network.string
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class MediaRepository(private val connectionRepository: NexRemoteConnectionRepository) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _state = MutableStateFlow(MediaState())
    val state: StateFlow<MediaState> = _state

    init {
        scope.launch {
            connectionRepository.messages.collect { payload ->
                if (payload.string("type") == "media_control" && payload.string("action") == "media_info") {
                    _state.value = MediaState(
                        volume = payload.int("volume") ?: -1,
                        isMuted = payload.bool("is_muted") ?: false,
                        isPlaying = payload.bool("is_playing") ?: false,
                        hasMedia = payload.bool("has_media") ?: false,
                        title = payload.string("title") ?: "No Media Playing",
                        artist = payload.string("artist").orEmpty(),
                    )
                }
            }
        }
    }

    fun play() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "play"))
    fun pause() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "pause"))
    fun stop() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "stop"))
    fun next() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "next"))
    fun previous() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "previous"))
    fun muteToggle() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "mute_toggle"))
    fun volumeUp() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "volume_up"))
    fun volumeDown() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "volume_down"))
    fun setVolume(volume: Int) = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "volume", "value" to volume))
    fun requestInfo() = connectionRepository.sendMessage(mapOf("type" to "media_control", "action" to "get_info"))
}
