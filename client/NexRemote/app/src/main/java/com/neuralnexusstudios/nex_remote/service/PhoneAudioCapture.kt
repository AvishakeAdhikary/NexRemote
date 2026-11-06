package com.neuralnexusstudios.nex_remote.service

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioPlaybackCaptureConfiguration
import android.media.AudioRecord
import android.media.projection.MediaProjection
import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.core.content.ContextCompat

/**
 * Captures the sound other apps are playing (Android 10+ AudioPlaybackCapture, tied to the screen
 * share's MediaProjection) and hands it out as 20 ms PCM16 LE stereo chunks at 48 kHz.
 *
 * This never opens the microphone. Android still requires the RECORD_AUDIO permission for playback
 * capture, and apps can opt out of being captured (their audio is then silent here).
 */
@RequiresApi(Build.VERSION_CODES.Q)
class PhoneAudioCapture(
    private val projection: MediaProjection,
    private val onChunk: (ptsUs: Long, pcm: ByteArray) -> Unit,
) {
    @Volatile private var running = false
    private var record: AudioRecord? = null
    private var thread: Thread? = null

    @SuppressLint("MissingPermission") // checked by the caller via canCapture()
    fun start(): Boolean {
        if (running) return true
        val config = AudioPlaybackCaptureConfiguration.Builder(projection)
            .addMatchingUsage(AudioAttributes.USAGE_MEDIA)
            .addMatchingUsage(AudioAttributes.USAGE_GAME)
            .addMatchingUsage(AudioAttributes.USAGE_UNKNOWN)
            .build()
        val format = AudioFormat.Builder()
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setSampleRate(SAMPLE_RATE)
            .setChannelMask(AudioFormat.CHANNEL_IN_STEREO)
            .build()
        val minBuffer = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_STEREO, AudioFormat.ENCODING_PCM_16BIT)
        val recorder = runCatching {
            AudioRecord.Builder()
                .setAudioFormat(format)
                .setBufferSizeInBytes(maxOf(minBuffer, CHUNK_BYTES * 4))
                .setAudioPlaybackCaptureConfig(config)
                .build()
        }.getOrElse {
            Log.w(TAG, "AudioRecord for playback capture failed", it)
            return false
        }
        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            recorder.release()
            return false
        }
        record = recorder
        running = true
        recorder.startRecording()
        thread = Thread({
            Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_AUDIO)
            val startNs = SystemClock.elapsedRealtimeNanos()
            var frames = 0L
            while (running) {
                val chunk = ByteArray(CHUNK_BYTES)
                var read = 0
                while (running && read < chunk.size) {
                    val n = recorder.read(chunk, read, chunk.size - read)
                    if (n <= 0) break
                    read += n
                }
                if (!running || read <= 0) break
                val ptsUs = (startNs / 1000) + frames * 1_000_000L / SAMPLE_RATE
                frames += read / BYTES_PER_FRAME
                onChunk(ptsUs, if (read == chunk.size) chunk else chunk.copyOf(read))
            }
        }, "NexRemotePhoneAudio").also { it.start() }
        return true
    }

    fun stop() {
        running = false
        runCatching { record?.stop() }
        thread?.join(500)
        runCatching { record?.release() }
        record = null
        thread = null
    }

    companion object {
        const val SAMPLE_RATE = 48_000
        const val CHANNELS = 2
        private const val BYTES_PER_FRAME = 2 * CHANNELS
        private const val CHUNK_BYTES = SAMPLE_RATE / 50 * BYTES_PER_FRAME // 20 ms
        private const val TAG = "PhoneAudioCapture"

        fun supported(): Boolean = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q

        fun canCapture(context: Context): Boolean =
            supported() && ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
    }
}
