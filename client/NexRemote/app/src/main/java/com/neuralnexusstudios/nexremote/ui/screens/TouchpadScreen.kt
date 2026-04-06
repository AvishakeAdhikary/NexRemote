package com.neuralnexusstudios.nexremote.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding

import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.TouchApp
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.ui.components.AppHapticStyle
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar
import com.neuralnexusstudios.nexremote.ui.components.rememberAppHaptics

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TouchpadScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val settings by appContainer.preferences.settings.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    var sensitivity by remember { mutableFloatStateOf(settings.gyroSensitivity.coerceIn(0.5f, 3f)) }
    val connection = appContainer.connectionRepository
    val performHaptic = rememberAppHaptics(settings.appHapticsEnabled)
    val touchpadAvailable = sessionState.connected && sessionState.featureStatus["touchpad"]?.available != false
    val touchpadReason = sessionState.featureStatus["touchpad"]?.reason
    var moveCarryX by remember { mutableFloatStateOf(0f) }
    var moveCarryY by remember { mutableFloatStateOf(0f) }
    var scrollCarryY by remember { mutableFloatStateOf(0f) }

    fun mouseClick(button: String, count: Int = 1) {
        if (!touchpadAvailable) return
        performHaptic(AppHapticStyle.Light)
        connection.sendMessage(mapOf("type" to "mouse", "action" to "click", "button" to button, "count" to count))
    }

    Scaffold(
        topBar = {
            AppTopBar(title = "Touchpad", onBack = onBack)
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            if (!touchpadAvailable) {
                Card {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Touchpad is not ready", style = MaterialTheme.typography.titleMedium)
                        Text(touchpadReason ?: "The PC server has not enabled mouse input yet.", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            Column {
                Text("Sensitivity", style = MaterialTheme.typography.titleMedium)
                Slider(
                    value = sensitivity,
                    onValueChange = { sensitivity = it },
                    valueRange = 0.5f..3f,
                )
                Text("${"%.1f".format(sensitivity)}x")
            }

            Row(
                modifier = Modifier.weight(1f),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(24.dp))
                        .pointerInput(sensitivity) {
                            detectDragGestures { change, dragAmount ->
                                change.consume()
                                if (!touchpadAvailable) return@detectDragGestures
                                val scaledDx = dragAmount.x * sensitivity + moveCarryX
                                val scaledDy = dragAmount.y * sensitivity + moveCarryY
                                val dx = scaledDx.toInt()
                                val dy = scaledDy.toInt()
                                moveCarryX = scaledDx - dx
                                moveCarryY = scaledDy - dy
                                if (dx == 0 && dy == 0) return@detectDragGestures
                                connection.sendMessage(
                                    mapOf(
                                        "type" to "mouse",
                                        "action" to "move_relative",
                                        "dx" to dx,
                                        "dy" to dy,
                                    ),
                                )
                            }
                        }
                        .pointerInput(Unit) {
                            detectTapGestures(
                                onTap = { mouseClick("left") },
                                onDoubleTap = { mouseClick("left", count = 2) },
                                onLongPress = { mouseClick("right") },
                            )
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Outlined.TouchApp, contentDescription = null, modifier = Modifier.size(56.dp))
                        Text("Tap to click, double-tap to double-click, long-press to right-click.")
                    }
                }
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(0.18f)
                        .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(24.dp))
                        .pointerInput(Unit) {
                            detectDragGestures { change, dragAmount ->
                                change.consume()
                                if (!touchpadAvailable) return@detectDragGestures
                                val scaledDy = (-dragAmount.y) + scrollCarryY
                                val dy = scaledDy.toInt()
                                scrollCarryY = scaledDy - dy
                                if (dy == 0) return@detectDragGestures
                                connection.sendMessage(
                                    mapOf(
                                        "type" to "mouse",
                                        "action" to "scroll",
                                        "dx" to 0,
                                        "dy" to dy,
                                    ),
                                )
                            }
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Text("Scroll")
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                Button(onClick = { mouseClick("left") }, modifier = Modifier.weight(1f), enabled = touchpadAvailable) { Text("Left") }
                Button(onClick = { mouseClick("middle") }, modifier = Modifier.weight(1f), enabled = touchpadAvailable) { Text("Middle") }
                Button(onClick = { mouseClick("right") }, modifier = Modifier.weight(1f), enabled = touchpadAvailable) { Text("Right") }
            }
        }
    }
}
