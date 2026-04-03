package com.neuralnexusstudios.nexremote.ui.components

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.HapticFeedbackConstants
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView

enum class AppHapticStyle(
    val viewConstant: Int,
    val durationMs: Long,
) {
    Light(HapticFeedbackConstants.CLOCK_TICK, 18),
    Confirm(HapticFeedbackConstants.KEYBOARD_TAP, 24),
    Heavy(HapticFeedbackConstants.LONG_PRESS, 36),
}

@Composable
fun rememberAppHaptics(enabled: Boolean): (AppHapticStyle) -> Unit {
    val context = LocalContext.current
    val view = LocalView.current
    return remember(context, view, enabled) {
        { style ->
            if (!enabled) return@remember
            val performed = view.performHapticFeedback(style.viewConstant)
            if (!performed) {
                runCatching {
                    val vibrator = context.defaultVibrator() ?: return@runCatching
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        vibrator.vibrate(VibrationEffect.createOneShot(style.durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
                    } else {
                        @Suppress("DEPRECATION")
                        vibrator.vibrate(style.durationMs)
                    }
                }
            }
        }
    }
}

private fun Context.defaultVibrator(): Vibrator? = when {
    Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
        getSystemService(VibratorManager::class.java)?.defaultVibrator
    }
    else -> {
        @Suppress("DEPRECATION")
        getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    }
}
