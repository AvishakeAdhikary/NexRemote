package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.PanTool
import androidx.compose.material.icons.outlined.TouchApp
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.composables.ui.components.Icon
import com.composables.ui.components.Slider
import com.composables.ui.components.Text
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.ui.components.AppHapticStyle
import com.neuralnexusstudios.nex_remote.ui.components.rememberAppHaptics
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxButton
import com.neuralnexusstudios.nex_remote.ui.design.NxButtonKind
import com.neuralnexusstudios.nex_remote.ui.design.NxCard
import com.neuralnexusstudios.nex_remote.ui.design.NxChip
import com.neuralnexusstudios.nex_remote.ui.design.NxScaffold
import com.neuralnexusstudios.nex_remote.ui.design.NxTone
import com.neuralnexusstudios.nex_remote.ui.design.NxType
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.roundToInt

private const val LONG_PRESS_MS = 450L
private const val TAP_MAX_MS = 280L

/**
 * Pointer acceleration: slow, precise movements map ~1:1, fast flicks cover the screen.
 * [speed] is finger speed in px per ms.
 */
internal fun pointerGain(speed: Float, sensitivity: Float): Float {
    val t = ((speed - 0.25f) / 2.25f).coerceIn(0f, 1f)
    return sensitivity * (1.15f + 2.35f * t)
}

@Composable
fun TouchpadScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val settings by appContainer.preferences.settings.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    var sensitivity by remember { mutableFloatStateOf(settings.gyroSensitivity.coerceIn(0.5f, 3f)) }
    var holdLeft by remember { mutableStateOf(false) }
    val connection = appContainer.connectionRepository
    val performHaptic = rememberAppHaptics(settings.appHapticsEnabled)
    val touchpadAvailable = sessionState.connected && sessionState.featureStatus["touchpad"]?.available != false
    val touchpadReason = sessionState.featureStatus["touchpad"]?.reason
    val preciseScroll = sessionState.capabilities?.preciseScroll == true

    fun mouseClick(button: String, count: Int = 1) {
        if (!touchpadAvailable) return
        performHaptic(AppHapticStyle.Light)
        connection.sendMessage(mapOf("type" to "mouse", "action" to "click", "button" to button, "count" to count))
    }

    fun move(dx: Int, dy: Int) {
        if (dx == 0 && dy == 0) return
        connection.sendMessage(mapOf("type" to "mouse", "action" to "move_relative", "dx" to dx, "dy" to dy))
    }

    // Scroll: precise hosts (1.2+) take raw wheel units (120 = one notch) for smooth scrolling;
    // older hosts only understand whole notches.
    val scrollCarry = remember { floatArrayOf(0f, 0f) }
    fun scroll(fingerDx: Float, fingerDy: Float) {
        val unitsPerPx = if (preciseScroll) 3.2f else 1f / 36f
        scrollCarry[0] += fingerDx * unitsPerPx
        scrollCarry[1] += -fingerDy * unitsPerPx
        val dx = scrollCarry[0].toInt()
        val dy = scrollCarry[1].toInt()
        scrollCarry[0] -= dx
        scrollCarry[1] -= dy
        if (dx == 0 && dy == 0) return
        connection.sendMessage(
            buildMap {
                put("type", "mouse")
                put("action", "scroll")
                put("dx", dx)
                put("dy", dy)
                if (preciseScroll) put("precise", true)
            },
        )
    }

    // Never leave the PC's left button stuck down.
    androidx.compose.runtime.DisposableEffect(Unit) {
        onDispose {
            if (holdLeft) connection.sendMessage(mapOf("type" to "mouse", "action" to "release", "button" to "left"))
        }
    }

    val latestSensitivity by rememberUpdatedState(sensitivity)
    val latestAvailable by rememberUpdatedState(touchpadAvailable)

    NxScaffold(title = "Touchpad", onBack = onBack) {
        Column(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (!touchpadAvailable) {
                NxCard(Modifier.fillMaxWidth(), tone = NxTone.Warning) {
                    Text("Touchpad is not ready", style = NxType.titleSmall)
                    Text(touchpadReason ?: "Connect to your PC first.", style = NxType.bodySmall, color = Nx.muted)
                }
            }

            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Speed", style = NxType.label, color = Nx.muted)
                Slider(value = sensitivity, onValueChange = { sensitivity = it }, valueRange = 0.5f..3f, modifier = Modifier.weight(1f))
                Text("${"%.1f".format(sensitivity)}x", style = NxType.label, color = Nx.primary)
            }

            // The pad: one finger moves (no dead zone, accelerated), tap = left click,
            // long-press = right click, two-finger tap = right click, two-finger drag = scroll.
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(28.dp))
                    .background(Nx.panelRaised)
                    .border(1.dp, Nx.border, RoundedCornerShape(28.dp))
                    .pointerInput(Unit) {
                        val carry = floatArrayOf(0f, 0f)
                        val slop = viewConfiguration.touchSlop
                        awaitEachGesture {
                            val down = awaitFirstDown(requireUnconsumed = false)
                            val start = down.uptimeMillis
                            var travel = 0f
                            var maxFingers = 1
                            var longPressed = false
                            var lastTime = start
                            while (true) {
                                val waitForLongPress = !longPressed && maxFingers == 1 && travel < slop
                                val event = if (waitForLongPress) {
                                    val remaining = LONG_PRESS_MS - (lastTime - start)
                                    withTimeoutOrNull(remaining.coerceAtLeast(1L)) { awaitPointerEvent(PointerEventPass.Main) }
                                } else {
                                    awaitPointerEvent(PointerEventPass.Main)
                                }
                                if (event == null) {
                                    longPressed = true
                                    if (latestAvailable) mouseClick("right")
                                    continue
                                }
                                lastTime = event.changes.maxOfOrNull { it.uptimeMillis } ?: lastTime
                                val pressed = event.changes.filter { it.pressed }
                                maxFingers = max(maxFingers, pressed.size)
                                if (pressed.isEmpty()) {
                                    val duration = (event.changes.firstOrNull()?.uptimeMillis ?: start) - start
                                    if (!longPressed && travel < slop * 1.5f && duration <= TAP_MAX_MS + 120) {
                                        if (maxFingers >= 2) mouseClick("right") else mouseClick("left")
                                    }
                                    break
                                }
                                if (!latestAvailable) {
                                    event.changes.forEach { it.consume() }
                                    continue
                                }
                                if (maxFingers >= 2) {
                                    // Two-finger scroll uses the average movement of the fingers down.
                                    var sx = 0f
                                    var sy = 0f
                                    pressed.forEach { c ->
                                        val d = c.positionChange()
                                        sx += d.x
                                        sy += d.y
                                    }
                                    sx /= pressed.size
                                    sy /= pressed.size
                                    travel += hypot(sx, sy)
                                    scroll(sx, sy)
                                } else {
                                    val c = pressed.first()
                                    val d = c.positionChange()
                                    val dist = hypot(d.x, d.y)
                                    travel += dist
                                    val dt = (c.uptimeMillis - c.previousUptimeMillis).coerceAtLeast(1L).toFloat()
                                    val gain = pointerGain(dist / dt, latestSensitivity)
                                    val fx = d.x * gain + carry[0]
                                    val fy = d.y * gain + carry[1]
                                    val ix = fx.roundToInt()
                                    val iy = fy.roundToInt()
                                    carry[0] = fx - ix
                                    carry[1] = fy - iy
                                    move(ix, iy)
                                }
                                event.changes.forEach { it.consume() }
                            }
                        }
                    },
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Outlined.TouchApp, contentDescription = null, tint = Nx.muted, modifier = Modifier.size(40.dp))
                    Text(
                        "Tap to click · hold for right-click\nTwo fingers: tap to right-click, drag to scroll",
                        style = NxType.bodySmall,
                        color = Nx.muted,
                        textAlign = TextAlign.Center,
                    )
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth().height(52.dp)) {
                NxButton("Left", onClick = { mouseClick("left") }, kind = NxButtonKind.Secondary, enabled = touchpadAvailable, modifier = Modifier.weight(1f))
                NxButton("Middle", onClick = { mouseClick("middle") }, kind = NxButtonKind.Secondary, enabled = touchpadAvailable, modifier = Modifier.weight(1f))
                NxButton("Right", onClick = { mouseClick("right") }, kind = NxButtonKind.Secondary, enabled = touchpadAvailable, modifier = Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.Center) {
                NxChip(
                    label = if (holdLeft) "Holding left button: tap to release" else "Hold left button (drag)",
                    selected = holdLeft,
                    icon = Icons.Outlined.PanTool,
                    enabled = touchpadAvailable,
                    onClick = {
                        holdLeft = !holdLeft
                        performHaptic(AppHapticStyle.Light)
                        connection.sendMessage(
                            mapOf("type" to "mouse", "action" to if (holdLeft) "press" else "release", "button" to "left"),
                        )
                    },
                )
            }
        }
    }
}
