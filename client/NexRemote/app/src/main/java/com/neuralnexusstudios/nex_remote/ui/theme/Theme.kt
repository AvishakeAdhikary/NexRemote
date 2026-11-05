package com.neuralnexusstudios.nex_remote.ui.theme

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.TextSelectionColors
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.shadow.Shadow
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.DpOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.composables.compose.ripple.rememberRippleIndication
import com.composables.ui.theme.ColorScheme
import com.composables.ui.theme.InteractionMode
import com.composables.ui.theme.LocalColorScheme
import com.composables.ui.theme.LocalInteractionMode
import com.composables.ui.theme.alphas
import com.composables.ui.theme.backgroundColor
import com.composables.ui.theme.borderColor
import com.composables.ui.theme.buttonShape
import com.composables.ui.theme.colors
import com.composables.ui.theme.controlColor
import com.composables.ui.theme.defaultIndication
import com.composables.ui.theme.defaultTextSelectionColors
import com.composables.ui.theme.destructiveColor
import com.composables.ui.theme.dialogShape
import com.composables.ui.theme.disabledAlpha
import com.composables.ui.theme.fieldColor
import com.composables.ui.theme.fieldShape
import com.composables.ui.theme.indications
import com.composables.ui.theme.inverseIndication
import com.composables.ui.theme.largeShape
import com.composables.ui.theme.mediumShape
import com.composables.ui.theme.menuShape
import com.composables.ui.theme.mutedColor
import com.composables.ui.theme.onBackgroundColor
import com.composables.ui.theme.onControlColor
import com.composables.ui.theme.onDestructiveColor
import com.composables.ui.theme.onFieldColor
import com.composables.ui.theme.onPanelColor
import com.composables.ui.theme.onPrimaryColor
import com.composables.ui.theme.onSecondaryColor
import com.composables.ui.theme.onSelectedControlColor
import com.composables.ui.theme.overlayShadow
import com.composables.ui.theme.panelColor
import com.composables.ui.theme.primaryColor
import com.composables.ui.theme.raisedShadow
import com.composables.ui.theme.ringColor
import com.composables.ui.theme.scrimColor
import com.composables.ui.theme.secondaryColor
import com.composables.ui.theme.selectedControlColor
import com.composables.ui.theme.shadows
import com.composables.ui.theme.shapes
import com.composables.ui.theme.sheetShape
import com.composables.ui.theme.smallShape
import com.composables.ui.theme.switchSelectedTrackColor
import com.composables.ui.theme.switchThumbColor
import com.composables.ui.theme.switchTrackColor
import com.composables.ui.theme.textSelectionColors
import com.composables.ui.theme.thumbColor
import com.composeunstyled.theme.ThemeComposable
import com.composeunstyled.theme.ThemeToken
import com.composeunstyled.theme.buildTheme
import com.neuralnexusstudios.nex_remote.core.model.ThemeMode

/*
 * NexRemote's Composables UI theme: red accents on black, dark by default.
 *
 * Composables UI components read their colours from the tokens in com.composables.ui.theme, so this
 * theme fills the same tokens (rather than using ComposablesTheme) and every library component picks
 * up the red/black palette. Extra NexRemote tokens (accent tint, success, warning) live below.
 */

/** Red tint used for icon wells, selected chips and highlighted cards. */
val accentSoftColor: ThemeToken<Color> = ThemeToken("nx_accent_soft")

/** Positive state (connected, running). */
val successColor: ThemeToken<Color> = ThemeToken("nx_success")

/** Needs-attention state (connecting, setup required). */
val warningColor: ThemeToken<Color> = ThemeToken("nx_warning")

/** Slightly raised surface inside a panel (rows, wells). */
val panelRaisedColor: ThemeToken<Color> = ThemeToken("nx_panel_raised")

object NxPalette {
    val Red = Color(0xFFE5202E)
    val RedBright = Color(0xFFFF4757)
    val RedDeep = Color(0xFFB0121E)
    val Black = Color(0xFF060606)
    val Carbon = Color(0xFF111111)
    val Graphite = Color(0xFF1A1A1A)
    val Steel = Color(0xFF262626)
    val Ash = Color(0xFF9A9A9A)
    val Bone = Color(0xFFF2F2F2)
}

@Composable
private fun pick(dark: Boolean, light: Color, darkColor: Color): Color =
    animateColorAsState(if (dark) darkColor else light, tween(180), label = "themeColor").value

private val NexRemoteComposablesTheme: ThemeComposable = buildTheme {
    val dark = LocalColorScheme.current == ColorScheme.Dark
    val interactionMode = LocalInteractionMode.current ?: InteractionMode.Touch

    properties[colors] = mapOf(
        backgroundColor to pick(dark, light = Color(0xFFF6F5F5), darkColor = NxPalette.Black),
        onBackgroundColor to pick(dark, light = Color(0xFF111111), darkColor = NxPalette.Bone),
        panelColor to pick(dark, light = Color.White, darkColor = NxPalette.Carbon),
        onPanelColor to pick(dark, light = Color(0xFF111111), darkColor = NxPalette.Bone),
        panelRaisedColor to pick(dark, light = Color(0xFFF1EFEF), darkColor = NxPalette.Graphite),
        mutedColor to pick(dark, light = Color(0xFF6B6B6B), darkColor = NxPalette.Ash),
        primaryColor to pick(dark, light = NxPalette.RedDeep, darkColor = NxPalette.Red),
        onPrimaryColor to Color.White,
        secondaryColor to pick(dark, light = Color(0xFFEDEBEB), darkColor = NxPalette.Steel),
        onSecondaryColor to pick(dark, light = Color(0xFF111111), darkColor = NxPalette.Bone),
        controlColor to pick(dark, light = Color(0xFFE4E1E1), darkColor = NxPalette.Steel),
        onControlColor to pick(dark, light = Color(0xFF6B6B6B), darkColor = NxPalette.Ash),
        thumbColor to Color.White,
        switchTrackColor to pick(dark, light = Color(0xFFE4E1E1), darkColor = NxPalette.Steel),
        switchSelectedTrackColor to pick(dark, light = NxPalette.RedDeep, darkColor = NxPalette.Red),
        switchThumbColor to Color.White,
        selectedControlColor to pick(dark, light = Color(0xFFFBE3E5), darkColor = Color(0xFF3A0A0F)),
        onSelectedControlColor to pick(dark, light = NxPalette.RedDeep, darkColor = NxPalette.RedBright),
        accentSoftColor to pick(dark, light = Color(0xFFFBE3E5), darkColor = Color(0xFF2A0A0D)),
        destructiveColor to pick(dark, light = Color(0xFFC62828), darkColor = Color(0xFFFF6B6B)),
        onDestructiveColor to Color.White,
        successColor to pick(dark, light = Color(0xFF1B7F45), darkColor = Color(0xFF3DDC84)),
        warningColor to pick(dark, light = Color(0xFFA35F00), darkColor = Color(0xFFFFB547)),
        borderColor to pick(dark, light = Color(0xFFE2DFDF), darkColor = Color(0xFF242424)),
        fieldColor to pick(dark, light = Color(0xFFF1EFEF), darkColor = NxPalette.Graphite),
        onFieldColor to pick(dark, light = Color(0xFF111111), darkColor = NxPalette.Bone),
        scrimColor to Color.Black.copy(alpha = if (dark) 0.6f else 0.4f),
        ringColor to NxPalette.Red.copy(alpha = 0.45f),
    )
    val selection = if (dark) NxPalette.RedBright else NxPalette.RedDeep
    properties[textSelectionColors] = mapOf(
        com.composables.ui.theme.defaultTextSelectionColors to TextSelectionColors(handleColor = selection, backgroundColor = selection.copy(alpha = 0.3f)),
    )
    properties[shapes] = mapOf(
        smallShape to RoundedCornerShape(8.dp),
        mediumShape to RoundedCornerShape(14.dp),
        largeShape to RoundedCornerShape(22.dp),
        buttonShape to RoundedCornerShape(100.dp),
        dialogShape to RoundedCornerShape(24.dp),
        sheetShape to RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        menuShape to RoundedCornerShape(16.dp),
        fieldShape to RoundedCornerShape(14.dp),
    )
    properties[shadows] = mapOf(
        raisedShadow to Shadow(radius = 16.dp, color = Color.Black, offset = DpOffset(0.dp, 4.dp), alpha = if (dark) 0.5f else 0.12f),
        overlayShadow to Shadow(radius = 28.dp, color = Color.Black, offset = DpOffset(0.dp, 10.dp), alpha = if (dark) 0.6f else 0.2f),
    )
    properties[alphas] = mapOf(disabledAlpha to 0.38f)

    defaultTextStyle = TextStyle(fontSize = 15.sp, lineHeight = 21.sp, fontWeight = FontWeight.Normal)

    val ripple = rememberRippleIndication(if (dark) Color.White.copy(alpha = 0.10f) else Color.Black.copy(alpha = 0.08f))
    val inverseRipple = rememberRippleIndication(if (dark) Color.Black.copy(alpha = 0.12f) else Color.White.copy(alpha = 0.16f))
    this.defaultIndication = ripple
    properties[indications] = mapOf(com.composables.ui.theme.defaultIndication to ripple, inverseIndication to inverseRipple)

    extend { content ->
        CompositionLocalProvider(LocalInteractionMode provides interactionMode) { content() }
    }
}

@Composable
fun NexRemoteTheme(
    mode: ThemeMode = ThemeMode.Dark,
    content: @Composable () -> Unit,
) {
    val dark = when (mode) {
        ThemeMode.Dark -> true
        ThemeMode.Light -> false
        ThemeMode.System -> isSystemInDarkTheme()
    }
    CompositionLocalProvider(LocalColorScheme provides if (dark) ColorScheme.Dark else ColorScheme.Light) {
        NexRemoteComposablesTheme { content() }
    }
}

/** True when the active NexRemote theme is dark. */
@Composable
fun isNxDark(): Boolean = LocalColorScheme.current == ColorScheme.Dark
