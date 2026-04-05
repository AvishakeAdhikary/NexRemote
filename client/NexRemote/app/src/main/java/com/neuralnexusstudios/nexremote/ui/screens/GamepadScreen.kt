package com.neuralnexusstudios.nexremote.ui.screens

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size

import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Layers
import androidx.compose.material.icons.outlined.ScreenRotationAlt
import androidx.compose.material.icons.outlined.Vibration
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.core.model.GamepadLayoutConfig
import com.neuralnexusstudios.nexremote.core.model.LayoutElement
import com.neuralnexusstudios.nexremote.ui.components.AppHapticStyle
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar
import com.neuralnexusstudios.nexremote.ui.components.rememberAppHaptics

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GamepadScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val layouts by appContainer.gamepadRepository.layouts.collectAsState()
    val activeLayout by appContainer.gamepadRepository.activeLayout.collectAsState()
    val settings by appContainer.preferences.settings.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    val context = LocalContext.current
    val hapticsEnabled = settings.appHapticsEnabled && activeLayout.hapticFeedback
    val performHaptic = rememberAppHaptics(hapticsEnabled)
    var showLayoutPicker by remember { mutableStateOf(false) }
    var editingLayout by remember { mutableStateOf<GamepadLayoutConfig?>(null) }
    var renameLayout by remember { mutableStateOf<GamepadLayoutConfig?>(null) }

    val gamepadAvailable = sessionState.connected &&
        sessionState.capabilities?.gamepadAvailable != false &&
        sessionState.featureStatus["gamepad"]?.available != false
    val gamepadReason = sessionState.featureStatus["gamepad"]?.reason
        ?: if (sessionState.capabilities?.gamepad == false) "Gamepad input is not supported by the PC server." else null

    DisposableEffect(activeLayout.id, activeLayout.gyroEnabled, activeLayout.accelEnabled, settings.gyroSensitivity) {
        if (!activeLayout.gyroEnabled && !activeLayout.accelEnabled) return@DisposableEffect onDispose { }
        val manager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val sensorType = if (activeLayout.gyroEnabled) Sensor.TYPE_GYROSCOPE else Sensor.TYPE_ACCELEROMETER
        val sensor = manager.getDefaultSensor(sensorType)
        if (sensor == null) return@DisposableEffect onDispose { }
        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                appContainer.gamepadRepository.sendGyro(
                    event.values[0] * settings.gyroSensitivity,
                    event.values[1] * settings.gyroSensitivity,
                    event.values[2] * settings.gyroSensitivity,
                )
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
        }
        manager.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_GAME)
        onDispose { manager.unregisterListener(listener) }
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = activeLayout.name,
                onBack = onBack,
                actions = {
                    IconButton(onClick = {
                        val updated = activeLayout.copy(hapticFeedback = !activeLayout.hapticFeedback)
                        appContainer.gamepadRepository.saveLayout(updated)
                        appContainer.gamepadRepository.setActive(updated)
                    }) {
                        Icon(Icons.Outlined.Vibration, contentDescription = "Toggle layout haptics")
                    }
                    IconButton(onClick = {
                        val updated = activeLayout.copy(gyroEnabled = !activeLayout.gyroEnabled)
                        appContainer.gamepadRepository.saveLayout(updated)
                        appContainer.gamepadRepository.setActive(updated)
                    }) {
                        Icon(Icons.Outlined.ScreenRotationAlt, contentDescription = "Toggle gyro")
                    }
                    IconButton(onClick = { editingLayout = activeLayout }) {
                        Icon(Icons.Outlined.Edit, contentDescription = "Edit layout")
                    }
                    IconButton(onClick = { showLayoutPicker = true }) {
                        Icon(Icons.Outlined.Layers, contentDescription = "Layouts")
                    }
                },
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (!gamepadAvailable) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = androidx.compose.material3.CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Text("Gamepad input is not ready", style = MaterialTheme.typography.titleMedium)
                        Text(
                            gamepadReason ?: "The PC server has not enabled gamepad support yet.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }

            BoxWithConstraints(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(24.dp)),
            ) {
                activeLayout.elements.forEach { element ->
                    val left = maxWidth * element.x
                    val top = maxHeight * element.y
                    Box(modifier = Modifier.offset(left, top)) {
                        when (element.type) {
                            "button" -> GamepadButton(element) {
                                if (gamepadAvailable) {
                                    if (it) performHaptic(AppHapticStyle.Light)
                                    appContainer.gamepadRepository.sendButton(element.action ?: element.label.orEmpty(), it)
                                }
                            }
                            "trigger" -> GamepadButton(element) {
                                if (gamepadAvailable) {
                                    if (it) performHaptic(AppHapticStyle.Light)
                                    appContainer.gamepadRepository.sendTrigger(element.trigger ?: "LT", if (it) 1f else 0f)
                                }
                            }
                            "macro" -> MacroButton(element) {
                                if (gamepadAvailable) {
                                    performHaptic(AppHapticStyle.Heavy)
                                    appContainer.gamepadRepository.fireMacro(element.macro)
                                }
                            }
                            "joystick" -> JoystickElement(element) { x, y ->
                                if (gamepadAvailable) {
                                    appContainer.gamepadRepository.sendJoystick(element.stick ?: "left", x, y)
                                }
                            }
                            "dpad" -> DpadElement(element) { direction, pressed ->
                                if (gamepadAvailable) {
                                    if (pressed) performHaptic(AppHapticStyle.Light)
                                    appContainer.gamepadRepository.sendDpad(direction, pressed)
                                }
                            }
                            "face_buttons" -> FaceButtonsElement(element) { button, pressed ->
                                if (gamepadAvailable) {
                                    if (pressed) performHaptic(AppHapticStyle.Light)
                                    appContainer.gamepadRepository.sendButton(button, pressed)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showLayoutPicker) {
        AlertDialog(
            onDismissRequest = { showLayoutPicker = false },
            title = { Text("Layouts") },
            text = {
                LazyColumn(modifier = Modifier.fillMaxWidth()) {
                    items(layouts, key = { it.id }) { layout ->
                        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                            Column(
                                modifier = Modifier.padding(12.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Text(layout.name, style = MaterialTheme.typography.titleMedium)
                                Text("${layout.mode} • ${layout.orientation}", style = MaterialTheme.typography.bodySmall)
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    TextButton(onClick = {
                                        appContainer.gamepadRepository.setActive(layout)
                                        showLayoutPicker = false
                                    }) { Text("Use") }
                                    TextButton(onClick = {
                                        editingLayout = layout
                                        showLayoutPicker = false
                                    }) { Text("Edit") }
                                    TextButton(onClick = {
                                        val duplicate = layout.copy(
                                            id = "${layout.id}_copy_${System.currentTimeMillis()}",
                                            name = "${layout.name} Copy",
                                        )
                                        appContainer.gamepadRepository.saveLayout(duplicate)
                                        appContainer.gamepadRepository.setActive(duplicate)
                                        showLayoutPicker = false
                                    }) { Text("Duplicate") }
                                    TextButton(onClick = { renameLayout = layout }) { Text("Rename") }
                                    if (layout.id !in listOf("standard_gamepad", "fps_layout", "racing_layout")) {
                                        TextButton(onClick = { appContainer.gamepadRepository.deleteLayout(layout.id) }) { Text("Delete") }
                                    }
                                }
                            }
                        }
                    }
                    item {
                        TextButton(onClick = {
                            editingLayout = GamepadLayoutConfig(
                                id = "custom_${System.currentTimeMillis()}",
                                name = "My Layout",
                                elements = emptyList(),
                            )
                            showLayoutPicker = false
                        }) {
                            Text("New Layout")
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showLayoutPicker = false }) { Text("Close") } },
        )
    }

    editingLayout?.let { layout ->
        LayoutEditorDialog(
            initialLayout = layout,
            onDismiss = { editingLayout = null },
            onSave = { updated ->
                appContainer.gamepadRepository.saveLayout(updated)
                appContainer.gamepadRepository.setActive(updated)
                editingLayout = null
            },
        )
    }

    renameLayout?.let { layout ->
        NameDialog(
            title = "Rename ${layout.name}",
            initialValue = layout.name,
            onDismiss = { renameLayout = null },
            onSubmit = { newName ->
                appContainer.gamepadRepository.saveLayout(layout.copy(name = newName))
                if (activeLayout.id == layout.id) {
                    appContainer.gamepadRepository.setActive(layout.copy(name = newName))
                }
                renameLayout = null
            },
        )
    }
}

@Composable
private fun GamepadButton(
    element: LayoutElement,
    onPressed: (Boolean) -> Unit,
) {
    Box(
        modifier = Modifier
            .size(element.width.dp, element.height.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.22f))
            .pointerInput(element.id) {
                detectTapGestures(
                    onPress = {
                        onPressed(true)
                        tryAwaitRelease()
                        onPressed(false)
                    },
                )
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(element.label ?: element.action.orEmpty())
    }
}

@Composable
private fun MacroButton(
    element: LayoutElement,
    onTap: () -> Unit,
) {
    Box(
        modifier = Modifier
            .size(element.width.dp, element.height.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.22f))
            .pointerInput(element.id) {
                detectTapGestures(onTap = { onTap() })
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(element.label ?: "Macro")
    }
}

@Composable
private fun FaceButtonsElement(
    element: LayoutElement,
    onButton: (String, Boolean) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(start = 48.dp)) {
            GamepadFaceButton("Y", onButton)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            GamepadFaceButton("X", onButton)
            GamepadFaceButton("B", onButton)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(start = 48.dp)) {
            GamepadFaceButton("A", onButton)
        }
    }
}

@Composable
private fun GamepadFaceButton(label: String, onButton: (String, Boolean) -> Unit) {
    Box(
        modifier = Modifier
            .size(44.dp)
            .clip(CircleShape)
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.24f))
            .pointerInput(label) {
                detectTapGestures(onPress = {
                    onButton(label, true)
                    tryAwaitRelease()
                    onButton(label, false)
                })
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(label)
    }
}

@Composable
private fun DpadElement(
    element: LayoutElement,
    onDirection: (String, Boolean) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(modifier = Modifier.padding(start = 36.dp)) { DpadButton("UP", onDirection) }
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            DpadButton("LEFT", onDirection)
            Box(modifier = Modifier.size(44.dp))
            DpadButton("RIGHT", onDirection)
        }
        Row(modifier = Modifier.padding(start = 36.dp)) { DpadButton("DOWN", onDirection) }
    }
}

@Composable
private fun DpadButton(label: String, onDirection: (String, Boolean) -> Unit) {
    Box(
        modifier = Modifier
            .size(44.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.18f))
            .pointerInput(label) {
                detectTapGestures(onPress = {
                    onDirection(label, true)
                    tryAwaitRelease()
                    onDirection(label, false)
                })
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(label.take(1))
    }
}

@Composable
private fun JoystickElement(
    element: LayoutElement,
    onMove: (Float, Float) -> Unit,
) {
    Box(
        modifier = Modifier
            .size(element.width.dp, element.height.dp)
            .clip(CircleShape)
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f))
            .pointerInput(element.id) {
                detectDragGestures(
                    onDragEnd = { onMove(0f, 0f) },
                    onDragCancel = { onMove(0f, 0f) },
                ) { change, _ ->
                    val x = ((change.position.x / size.width) * 2f - 1f).coerceIn(-1f, 1f)
                    val y = (((change.position.y / size.height) * 2f - 1f) * -1f).coerceIn(-1f, 1f)
                    onMove(x, y)
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(MaterialTheme.colorScheme.primary, CircleShape),
        )
    }
}
