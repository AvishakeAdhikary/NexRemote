package com.neuralnexusstudios.nex_remote.ui.components

import android.content.Context
import android.media.AudioAttributes
import android.os.Build
import android.os.VibrationAttributes
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.HapticFeedbackConstants
import android.view.View
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView

/**
 * Haptic styles, following https://developer.android.com/develop/ui/views/haptics/haptic-feedback:
 * semantic View constants for ordinary UI, predefined VibrationEffects (no createOneShot except as a
 * last-resort fallback) for the gamepad.
 */
enum class AppHapticStyle {
    /** Button / key press. */
    Light,

    /** Button / key release. */
    Release,

    /** A successful action. */
    Confirm,

    /** An emphatic action (macro, long press). */
    Heavy,
}

private fun AppHapticStyle.viewConstant(): Int = when (this) {
    AppHapticStyle.Light -> HapticFeedbackConstants.VIRTUAL_KEY
    AppHapticStyle.Release ->
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) HapticFeedbackConstants.VIRTUAL_KEY_RELEASE else HapticFeedbackConstants.CLOCK_TICK
    AppHapticStyle.Confirm ->
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) HapticFeedbackConstants.CONFIRM else HapticFeedbackConstants.VIRTUAL_KEY
    AppHapticStyle.Heavy -> HapticFeedbackConstants.LONG_PRESS
}

/**
 * Haptics for ordinary UI ([game] = false): View.performHapticFeedback, which honours the user's
 * system "Touch feedback" setting.
 *
 * Gamepad haptics ([game] = true) are a controller feature the user switches on per layout, so they
 * play predefined effects through the Vibrator with game/media attributes. They still work when
 * system touch feedback is off (the cause of "haptics never turn on" on many phones), and
 * CLOCK_TICK-style constants are too faint for some vibration motors.
 */
@Composable
fun rememberAppHaptics(enabled: Boolean, game: Boolean = false): (AppHapticStyle) -> Unit {
    val context = LocalContext.current
    val view = LocalView.current
    return remember(context, view, enabled, game) {
        val vibrator = if (game) context.defaultVibrator() else null
        { style ->
            if (enabled) {
                if (game && vibrator != null && vibrator.hasVibrator()) {
                    runCatching { vibrator.play(style) }.onFailure { view.performUiHaptic(style) }
                } else {
                    view.performUiHaptic(style)
                }
            }
        }
    }
}

private fun View.performUiHaptic(style: AppHapticStyle) {
    performHapticFeedback(style.viewConstant())
}

private fun Vibrator.play(style: AppHapticStyle) {
    val effect = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        VibrationEffect.createPredefined(
            when (style) {
                AppHapticStyle.Light, AppHapticStyle.Confirm -> VibrationEffect.EFFECT_CLICK
                AppHapticStyle.Release -> VibrationEffect.EFFECT_TICK
                AppHapticStyle.Heavy -> VibrationEffect.EFFECT_HEAVY_CLICK
            },
        )
    } else {
        // Android 8/9 fallback: short one-shots (the guide's last-resort option).
        VibrationEffect.createOneShot(
            when (style) {
                AppHapticStyle.Release -> 10L
                AppHapticStyle.Light, AppHapticStyle.Confirm -> 18L
                AppHapticStyle.Heavy -> 35L
            },
            VibrationEffect.DEFAULT_AMPLITUDE,
        )
    }
    when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU ->
            vibrate(effect, VibrationAttributes.createForUsage(VibrationAttributes.USAGE_MEDIA))
        else -> {
            @Suppress("DEPRECATION")
            vibrate(effect, AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME).build())
        }
    }
}

private fun Context.defaultVibrator(): Vibrator? = when {
    Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> getSystemService(VibratorManager::class.java)?.defaultVibrator
    else -> {
        @Suppress("DEPRECATION")
        getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    }
}
