package com.neuralnexusstudios.nex_remote.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Build
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import com.neuralnexusstudios.nex_remote.core.network.double
import com.neuralnexusstudios.nex_remote.core.network.int
import com.neuralnexusstudios.nex_remote.core.network.string
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.JsonObject

/**
 * Performs taps, swipes and Back/Home/Recents sent from the user's paired PC while this phone
 * is sharing its screen with that PC and "Allow PC control" is on (checked by
 * PhoneScreenRepository before calling [perform]).
 *
 * It does not read window content, observe what the user types, or collect any data: the
 * service config requests no content retrieval, and accessibility events are ignored.
 */
class NexRemoteControlService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        _running.value = true
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit

    override fun onInterrupt() = Unit

    override fun onUnbind(intent: android.content.Intent?): Boolean {
        clear()
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        clear()
        super.onDestroy()
    }

    private fun clear() {
        if (instance === this) instance = null
        _running.value = false
    }

    /** Executes one `phone_screen` input message. Returns false if it was invalid or not dispatched. */
    fun perform(message: JsonObject): Boolean {
        return when (message.string("input_action")) {
            "key" -> when (message.string("key")) {
                "back" -> performGlobalAction(GLOBAL_ACTION_BACK)
                "home" -> performGlobalAction(GLOBAL_ACTION_HOME)
                "recents" -> performGlobalAction(GLOBAL_ACTION_RECENTS)
                else -> false
            }
            "tap", "long_press" -> {
                val (x, y) = toScreen(message.double("normalized_x"), message.double("normalized_y")) ?: return false
                val fallback = if (message.string("input_action") == "tap") 50 else 600
                gesture(Path().apply { moveTo(x, y) }, durationOf(message, fallback))
            }
            "swipe" -> {
                val (x, y) = toScreen(message.double("normalized_x"), message.double("normalized_y")) ?: return false
                val (ex, ey) = toScreen(message.double("end_x"), message.double("end_y")) ?: return false
                gesture(Path().apply { moveTo(x, y); lineTo(ex, ey) }, durationOf(message, 250))
            }
            else -> false
        }
    }

    private fun durationOf(message: JsonObject, fallback: Int): Long =
        (message.int("duration_ms") ?: fallback).coerceIn(1, 5000).toLong()

    private fun gesture(path: Path, durationMs: Long): Boolean =
        dispatchGesture(
            GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(path, 0, durationMs)).build(),
            null,
            null,
        )

    /** Normalized (0..1) coordinates of the shared picture -> real display pixels. */
    private fun toScreen(nx: Double?, ny: Double?): Pair<Float, Float>? {
        if (nx == null || ny == null) return null
        val windowManager = getSystemService(WindowManager::class.java)
        val (w, h) = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            windowManager.maximumWindowMetrics.bounds.let { it.width() to it.height() }
        } else {
            @Suppress("DEPRECATION")
            android.util.DisplayMetrics().also { windowManager.defaultDisplay.getRealMetrics(it) }.let { it.widthPixels to it.heightPixels }
        }
        val x = (nx.coerceIn(0.0, 1.0) * (w - 1)).toFloat()
        val y = (ny.coerceIn(0.0, 1.0) * (h - 1)).toFloat()
        return x to y
    }

    companion object {
        @Volatile
        var instance: NexRemoteControlService? = null
            private set

        private val _running = MutableStateFlow(false)
        val running: StateFlow<Boolean> = _running

        val isRunning: Boolean
            get() = instance != null
    }
}
