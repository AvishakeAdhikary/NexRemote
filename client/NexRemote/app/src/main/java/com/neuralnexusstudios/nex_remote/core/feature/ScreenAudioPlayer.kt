package com.neuralnexusstudios.nex_remote.core.feature

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import com.neuralnexusstudios.nex_remote.core.model.ScreenAudioFormat

class ScreenAudioPlayer {
    private val lock = Any()
    private var track: AudioTrack? = null
    private var currentFormat: ScreenAudioFormat? = null

    fun configure(format: ScreenAudioFormat): Boolean {
        synchronized(lock) {
            if (currentFormat == format && track?.state == AudioTrack.STATE_INITIALIZED) {
                if (track?.playState != AudioTrack.PLAYSTATE_PLAYING) {
                    track?.play()
                }
                return true
            }

            releaseLocked()

            val channelMask = when (format.channels) {
                1 -> AudioFormat.CHANNEL_OUT_MONO
                2 -> AudioFormat.CHANNEL_OUT_STEREO
                else -> return false
            }

            val encoding = when (format.encoding.lowercase()) {
                "pcm16", "pcm_s16le" -> AudioFormat.ENCODING_PCM_16BIT
                else -> return false
            }

            val minBufferSize = AudioTrack.getMinBufferSize(format.sampleRate, channelMask, encoding)
            if (minBufferSize <= 0) {
                return false
            }

            val audioTrack = AudioTrack(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
                AudioFormat.Builder()
                    .setEncoding(encoding)
                    .setSampleRate(format.sampleRate)
                    .setChannelMask(channelMask)
                    .build(),
                minBufferSize.coerceAtLeast(format.channels * format.bytesPerSample * 2048),
                AudioTrack.MODE_STREAM,
                AudioManager.AUDIO_SESSION_ID_GENERATE,
            )

            if (audioTrack.state != AudioTrack.STATE_INITIALIZED) {
                audioTrack.release()
                return false
            }

            audioTrack.play()
            track = audioTrack
            currentFormat = format
            return true
        }
    }

    fun playChunk(bytes: ByteArray) {
        synchronized(lock) {
            val currentTrack = track ?: return
            if (bytes.isEmpty()) {
                return
            }

            if (currentTrack.playState != AudioTrack.PLAYSTATE_PLAYING) {
                currentTrack.play()
            }

            currentTrack.write(bytes, 0, bytes.size, AudioTrack.WRITE_BLOCKING)
        }
    }

    fun stop() {
        synchronized(lock) {
            releaseLocked()
        }
    }

    private fun releaseLocked() {
        track?.run {
            runCatching { pause() }
            runCatching { flush() }
            release()
        }
        track = null
        currentFormat = null
    }
}
