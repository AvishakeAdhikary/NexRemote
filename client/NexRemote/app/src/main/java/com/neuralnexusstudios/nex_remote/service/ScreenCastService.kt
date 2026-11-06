package com.neuralnexusstudios.nex_remote.service

import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.util.Log
import android.view.Surface
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.IntentCompat
import com.neuralnexusstudios.nex_remote.MainActivity
import com.neuralnexusstudios.nex_remote.NexRemoteApplication
import com.neuralnexusstudios.nex_remote.R
import com.neuralnexusstudios.nex_remote.core.feature.PhoneScreenRepository

/**
 * Foreground service (type mediaProjection) that mirrors the display into an H.264 encoder and
 * hands encoded access units to [PhoneScreenRepository], which sends them to the connected PC.
 *
 * It only runs after the user taps "Share my screen" and accepts the system capture dialog,
 * shows an ongoing notification with a Stop action, and stops when the user stops it, the
 * system revokes the projection, or the PC connection drops. Nothing is written to storage.
 */
class ScreenCastService : Service() {
    private var projection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var encoder: MediaCodec? = null
    private var encoderThread: HandlerThread? = null
    private var audio: PhoneAudioCapture? = null
    private var width = 0
    private var height = 0
    private var rotation = 0
    @Volatile private var running = false

    private val repository: PhoneScreenRepository
        get() = (application as NexRemoteApplication).appContainer.phoneScreenRepository

    private val projectionCallback = object : MediaProjection.Callback() {
        override fun onStop() {
            stopCapture("Screen sharing was stopped.")
        }

        override fun onCapturedContentResize(width: Int, height: Int) {
            restartEncoderIfNeeded()
        }
    }

    private val displayListener = object : DisplayManager.DisplayListener {
        override fun onDisplayAdded(displayId: Int) = Unit
        override fun onDisplayRemoved(displayId: Int) = Unit
        override fun onDisplayChanged(displayId: Int) = restartEncoderIfNeeded()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopCapture(null)
                return START_NOT_STICKY
            }
            ACTION_START -> startCapture(intent)
        }
        return START_NOT_STICKY
    }

    private fun startCapture(intent: Intent) {
        // Android 14+: the foreground service must be running before getMediaProjection().
        ServiceCompat.startForeground(
            this,
            NOTIFICATION_ID,
            buildNotification(),
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION else 0,
        )
        val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED)
        val data = IntentCompat.getParcelableExtra(intent, EXTRA_RESULT_DATA, Intent::class.java)
        if (resultCode != Activity.RESULT_OK || data == null || running) {
            if (!running) stopCapture("Screen sharing needs your permission.")
            return
        }
        val manager = getSystemService(MediaProjectionManager::class.java)
        val mediaProjection = runCatching { manager.getMediaProjection(resultCode, data) }.getOrNull()
        if (mediaProjection == null) {
            stopCapture("Android did not allow screen capture.")
            return
        }
        projection = mediaProjection
        mediaProjection.registerCallback(projectionCallback, Handler(mainLooper))
        running = true
        current = this
        getSystemService(DisplayManager::class.java).registerDisplayListener(displayListener, Handler(mainLooper))
        try {
            val (w, h, dpi) = captureSize()
            val surface = startEncoder(w, h)
            virtualDisplay = mediaProjection.createVirtualDisplay(
                "NexRemote screen share", w, h, dpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, surface, null, null,
            )
            repository.onEncoderStarted(w, h, FRAME_RATE, rotation)
        } catch (error: Exception) {
            Log.w(TAG, "Could not start screen capture", error)
            stopCapture("Screen sharing could not start: ${error.message}")
        }
    }

    /** Display size scaled so the long side is at most [MAX_LONG_SIDE], rounded to multiples of 16. */
    private fun captureSize(): Triple<Int, Int, Int> {
        val windowManager = getSystemService(WindowManager::class.java)
        val (realW, realH) = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            windowManager.maximumWindowMetrics.bounds.let { it.width() to it.height() }
        } else {
            @Suppress("DEPRECATION")
            android.util.DisplayMetrics().also { windowManager.defaultDisplay.getRealMetrics(it) }.let { it.widthPixels to it.heightPixels }
        }
        @Suppress("DEPRECATION")
        rotation = windowManager.defaultDisplay.rotation * 90
        val scale = minOf(1.0, MAX_LONG_SIDE.toDouble() / maxOf(realW, realH))
        val w = ((realW * scale).toInt() / 16 * 16).coerceAtLeast(16)
        val h = ((realH * scale).toInt() / 16 * 16).coerceAtLeast(16)
        return Triple(w, h, resources.displayMetrics.densityDpi)
    }

    private fun startEncoder(w: Int, h: Int): Surface {
        width = w
        height = h
        val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, w, h).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
            setInteger(MediaFormat.KEY_BIT_RATE, (w * h * 4).coerceIn(2_000_000, 8_000_000))
            setInteger(MediaFormat.KEY_FRAME_RATE, FRAME_RATE)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
            // Re-send the last frame on a static screen so a newly opened PC viewer gets a picture.
            setLong(MediaFormat.KEY_REPEAT_PREVIOUS_FRAME_AFTER, 250_000L)
            // Baseline profile: no B-frames and decodable by every WebCodecs H.264 decoder.
            setInteger(MediaFormat.KEY_PROFILE, MediaCodecInfo.CodecProfileLevel.AVCProfileBaseline)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
            // Repeat SPS/PPS before every keyframe (where supported) so a viewer can join mid-stream.
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) setInteger(MediaFormat.KEY_PREPEND_HEADER_TO_SYNC_FRAMES, 1)
        }
        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        val thread = HandlerThread("ScreenCastEncoder").also { it.start() }
        codec.setCallback(EncoderCallback(), Handler(thread.looper))
        codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        val surface = codec.createInputSurface()
        codec.start()
        encoder = codec
        encoderThread = thread
        return surface
    }

    private fun releaseEncoder() {
        encoder?.let { codec ->
            runCatching { codec.stop() }
            runCatching { codec.release() }
        }
        encoder = null
        encoderThread?.quitSafely()
        encoderThread = null
    }

    /** Rotation or a resolution change: new encoder at the new size, same projection and display. */
    private fun restartEncoderIfNeeded() {
        if (!running) return
        val display = virtualDisplay ?: return
        val (w, h, dpi) = captureSize()
        if (w == width && h == height) return
        releaseEncoder()
        val surface = startEncoder(w, h)
        display.resize(w, h, dpi)
        display.surface = surface
        repository.onEncoderStarted(w, h, FRAME_RATE, rotation)
    }

    private inner class EncoderCallback : MediaCodec.Callback() {
        override fun onInputBufferAvailable(codec: MediaCodec, index: Int) = Unit

        override fun onOutputBufferAvailable(codec: MediaCodec, index: Int, info: MediaCodec.BufferInfo) {
            if (codec !== encoder) return
            try {
                val buffer = codec.getOutputBuffer(index)
                if (buffer != null && info.size > 0) {
                    val bytes = ByteArray(info.size)
                    buffer.position(info.offset)
                    buffer.get(bytes, 0, info.size)
                    val flags = when {
                        info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0 -> PhoneScreenRepository.FLAG_CONFIG
                        info.flags and MediaCodec.BUFFER_FLAG_KEY_FRAME != 0 -> PhoneScreenRepository.FLAG_KEYFRAME
                        else -> 0
                    }
                    repository.onEncodedFrame(flags, info.presentationTimeUs, bytes)
                }
                codec.releaseOutputBuffer(index, false)
            } catch (_: IllegalStateException) {
                // encoder was released while this buffer was in flight
            }
        }

        override fun onError(codec: MediaCodec, e: MediaCodec.CodecException) {
            Log.w(TAG, "Encoder error", e)
            if (codec === encoder) stopCapture("The video encoder stopped: ${e.diagnosticInfo}")
        }

        override fun onOutputFormatChanged(codec: MediaCodec, format: MediaFormat) = Unit
    }

    private fun stopCapture(message: String?) {
        val wasRunning = running
        running = false
        if (current === this) current = null
        runCatching { getSystemService(DisplayManager::class.java).unregisterDisplayListener(displayListener) }
        setAudioEnabled(false)
        virtualDisplay?.release()
        virtualDisplay = null
        releaseEncoder()
        projection?.let { p ->
            runCatching { p.unregisterCallback(projectionCallback) }
            runCatching { p.stop() }
        }
        projection = null
        if (wasRunning || message != null) repository.onCaptureStopped(message)
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        if (running) stopCapture(null)
        super.onDestroy()
    }

    /** Start or stop sending this phone's playback audio. Returns whether audio is now active. */
    fun setAudioEnabled(enabled: Boolean): Boolean {
        if (!enabled) {
            audio?.stop()
            audio = null
            return false
        }
        if (audio != null) return true
        val p = projection ?: return false
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q || !running || !PhoneAudioCapture.canCapture(this)) return false
        val capture = PhoneAudioCapture(p) { pts, pcm -> repository.onAudioChunk(pts, pcm) }
        if (!capture.start()) return false
        audio = capture
        return true
    }

    private fun buildNotification(): Notification {
        val manager = getSystemService(NotificationManager::class.java)
        if (manager.getNotificationChannel(CHANNEL_ID) == null) {
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, getString(R.string.screen_share_channel), NotificationManager.IMPORTANCE_LOW).apply {
                    description = getString(R.string.screen_share_channel_description)
                },
            )
        }
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val stop = PendingIntent.getService(
            this, 1, Intent(this, ScreenCastService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_monochrome)
            .setContentTitle(getString(R.string.screen_share_notification_title))
            .setContentText(getString(R.string.screen_share_notification_text))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setContentIntent(open)
            .addAction(0, getString(R.string.screen_share_stop), stop)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    companion object {
        const val ACTION_START = "com.neuralnexusstudios.nex_remote.action.START_SCREEN_SHARE"
        const val ACTION_STOP = "com.neuralnexusstudios.nex_remote.action.STOP_SCREEN_SHARE"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        private const val CHANNEL_ID = "screen_share"
        private const val NOTIFICATION_ID = 4201
        private const val FRAME_RATE = 30
        private const val MAX_LONG_SIDE = 1600
        private const val TAG = "ScreenCastService"

        @Volatile
        private var current: ScreenCastService? = null

        /** Start/stop phone audio for the running share. Returns whether audio is active. */
        fun setAudio(enabled: Boolean): Boolean = current?.setAudioEnabled(enabled) ?: false

        /** Ask the encoder for an IDR frame (a PC viewer just opened or lost sync). */
        fun requestKeyframe() {
            val codec = current?.encoder ?: return
            runCatching {
                codec.setParameters(Bundle().apply { putInt(MediaCodec.PARAMETER_KEY_REQUEST_SYNC_FRAME, 0) })
            }
        }
    }
}
