package com.neuralnexusstudios.nexremote.ui.screens

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Layers
import androidx.compose.material.icons.outlined.ScreenRotationAlt
import androidx.compose.material.icons.outlined.Vibration
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.core.feature.GamepadRepository
import com.neuralnexusstudios.nexremote.core.model.BuiltInGamepadLayoutIds
import com.neuralnexusstudios.nexremote.core.model.GamepadCanvasConfig
import com.neuralnexusstudios.nexremote.core.model.GamepadLayoutConfig
import com.neuralnexusstudios.nexremote.core.model.LayoutElement
import com.neuralnexusstudios.nexremote.core.model.canvasFor
import com.neuralnexusstudios.nexremote.core.model.fitIntoCanvas
import com.neuralnexusstudios.nexremote.core.model.normalizeForStorage
import com.neuralnexusstudios.nexremote.ui.components.AppHapticStyle
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar
import com.neuralnexusstudios.nexremote.ui.components.rememberAppHaptics
import kotlin.math.abs
import kotlin.math.min

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GamepadScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val repository = appContainer.gamepadRepository
    val layouts by repository.layouts.collectAsState()
    val activeLayout by repository.activeLayout.collectAsState()
    val settings by appContainer.preferences.settings.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    val context = LocalContext.current
    val performHaptic = rememberAppHaptics(settings.appHapticsEnabled && activeLayout.hapticFeedback)
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
        val sensor = manager.getDefaultSensor(if (activeLayout.gyroEnabled) Sensor.TYPE_GYROSCOPE else Sensor.TYPE_ACCELEROMETER)
            ?: return@DisposableEffect onDispose { }
        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                repository.sendGyro(
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
                        repository.saveLayout(updated)
                        repository.setActive(updated)
                    }) { Icon(Icons.Outlined.Vibration, contentDescription = "Toggle layout haptics") }
                    IconButton(onClick = {
                        val updated = activeLayout.copy(gyroEnabled = !activeLayout.gyroEnabled)
                        repository.saveLayout(updated)
                        repository.setActive(updated)
                    }) { Icon(Icons.Outlined.ScreenRotationAlt, contentDescription = "Toggle gyro") }
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
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Gamepad input is not ready", style = MaterialTheme.typography.titleMedium)
                        Text(
                            gamepadReason ?: "The PC server has not enabled gamepad support yet.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                AssistChip(onClick = { editingLayout = activeLayout }, label = { Text(if (activeLayout.layoutKind == "touch_mapper") "Touch Mapper" else "Classic Controller") })
                AssistChip(onClick = {}, label = { Text("Mode: ${activeLayout.mode.uppercase()}") })
                if (activeLayout.gyroEnabled) AssistChip(onClick = {}, label = { Text("Gyro On") })
                if (activeLayout.accelEnabled) AssistChip(onClick = {}, label = { Text("Accel On") })
            }

            BoxWithConstraints(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(28.dp))
                    .background(Brush.linearGradient(listOf(Color(0xFF111827), Color(0xFF1F2937), Color(0xFF0F172A)))),
            ) {
                val isLandscape = maxWidth > maxHeight
                val displayCanvas = remember(activeLayout, isLandscape) { activeLayout.canvasFor(isLandscape).fitIntoCanvas() }
                RuntimeCanvas(
                    canvas = displayCanvas,
                    repository = repository,
                    gamepadAvailable = gamepadAvailable,
                    performHaptic = performHaptic,
                )
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
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (layout.id == activeLayout.id) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHighest,
                            ),
                        ) {
                            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(layout.name, style = MaterialTheme.typography.titleMedium)
                                Text("${layout.mode.uppercase()} • ${if (layout.layoutKind == "touch_mapper") "Touch Mapper" else "Classic Controller"}", style = MaterialTheme.typography.bodySmall)
                                Row(modifier = Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    TextButton(onClick = {
                                        repository.setActive(layout)
                                        showLayoutPicker = false
                                    }) { Text("Use") }
                                    TextButton(onClick = {
                                        editingLayout = layout
                                        showLayoutPicker = false
                                    }) { Text("Edit") }
                                    TextButton(onClick = {
                                        val duplicate = layout.copy(id = "${layout.id}_copy_${System.currentTimeMillis()}", name = "${layout.name} Copy").normalizeForStorage()
                                        repository.saveLayout(duplicate)
                                        repository.setActive(duplicate)
                                        showLayoutPicker = false
                                    }) { Text("Duplicate") }
                                    TextButton(onClick = {
                                        renameLayout = layout
                                        showLayoutPicker = false
                                    }) { Text("Rename") }
                                    if (!BuiltInGamepadLayoutIds.contains(layout.id)) {
                                        TextButton(onClick = { repository.deleteLayout(layout.id) }) { Text("Delete") }
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
                                layoutKind = "touch_mapper",
                                mode = activeLayout.mode,
                                gyroEnabled = activeLayout.gyroEnabled,
                                accelEnabled = activeLayout.accelEnabled,
                                hapticFeedback = true,
                            ).normalizeForStorage()
                            showLayoutPicker = false
                        }) { Text("New Layout") }
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
                repository.saveLayout(updated)
                repository.setActive(updated)
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
                val updated = layout.copy(name = newName)
                repository.saveLayout(updated)
                if (activeLayout.id == layout.id) repository.setActive(updated)
                renameLayout = null
            },
        )
    }
}

@Composable
private fun RuntimeCanvas(
    canvas: GamepadCanvasConfig,
    repository: GamepadRepository,
    gamepadAvailable: Boolean,
    performHaptic: (AppHapticStyle) -> Unit,
) {
    BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(12.dp)) {
        if (canvas.showSafeZones) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val padX = size.width * canvas.safePaddingRatio
                val padY = size.height * canvas.safePaddingRatio
                drawRoundRect(
                    color = Color.White.copy(alpha = 0.11f),
                    topLeft = Offset(padX, padY),
                    size = Size(size.width - padX * 2f, size.height - padY * 2f),
                    style = Stroke(width = 2.dp.toPx()),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(32.dp.toPx(), 32.dp.toPx()),
                )
            }
        }

        canvas.elements.sortedBy { it.zIndex }.forEach { element ->
            val left = maxWidth * (element.centerX - element.widthRatio / 2f)
            val top = maxHeight * (element.centerY - element.heightRatio / 2f)
            val width = maxWidth * element.widthRatio
            val height = maxHeight * element.heightRatio
            Box(
                modifier = Modifier
                    .offset(x = left, y = top)
                    .size(width = width, height = height),
            ) {
                when (element.type) {
                    "button", "utility" -> RuntimeButton(element) { pressed ->
                        if (gamepadAvailable) {
                            if (pressed) performHaptic(AppHapticStyle.Light)
                            repository.sendButton(element.action ?: element.bindingValue.orEmpty(), pressed)
                        }
                    }

                    "trigger" -> RuntimeButton(element) { pressed ->
                        if (gamepadAvailable) {
                            if (pressed) performHaptic(AppHapticStyle.Light)
                            repository.sendTrigger(element.trigger ?: element.bindingValue ?: "LT", if (pressed) 1f else 0f)
                        }
                    }

                    "macro" -> RuntimeButton(
                        element = element.copy(fillColor = if (element.fillColor == 0L) 0xCC7C3AED else element.fillColor),
                    ) { pressed ->
                        if (pressed && gamepadAvailable) {
                            performHaptic(AppHapticStyle.Heavy)
                            repository.fireMacro(element.macro)
                        }
                    }

                    "joystick" -> RuntimeJoystick(element) { x, y ->
                        if (gamepadAvailable) {
                            repository.sendJoystick(element.stick ?: element.bindingValue ?: "left", x, y)
                        }
                    }

                    "dpad" -> RuntimeDpad(element) { direction, pressed ->
                        if (gamepadAvailable) {
                            if (pressed) performHaptic(AppHapticStyle.Light)
                            repository.sendDpad(direction, pressed)
                        }
                    }

                    "face_buttons" -> RuntimeFaceButtons { button, pressed ->
                        if (gamepadAvailable) {
                            if (pressed) performHaptic(AppHapticStyle.Light)
                            repository.sendButton(button, pressed)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RuntimeButton(
    element: LayoutElement,
    onPressed: (Boolean) -> Unit,
) {
    val fill = element.fillColor.asGamepadColor(element.alpha)
    val stroke = element.strokeColor.asGamepadColor()
    Surface(
        modifier = Modifier
            .fillMaxSize()
            .pointerInput(element.id) {
                detectTapGestures(onPress = {
                    onPressed(true)
                    tryAwaitRelease()
                    onPressed(false)
                })
            },
        shape = RoundedCornerShape(if (element.type == "utility") 18.dp else 24.dp),
        color = Color.Transparent,
        border = androidx.compose.foundation.BorderStroke(1.4.dp, stroke.copy(alpha = 0.7f)),
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Brush.verticalGradient(listOf(fill.copy(alpha = fill.alpha * 0.94f), fill.copy(alpha = fill.alpha * 0.56f)))),
            contentAlignment = Alignment.Center,
        ) {
            if (element.labelVisible) {
                Text(
                    text = element.label ?: element.action ?: element.trigger ?: element.stick.orEmpty(),
                    color = element.labelColor.asGamepadColor(),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(horizontal = 8.dp),
                )
            }
        }
    }
}

@Composable
fun RuntimeFaceButtons(onButton: (String, Boolean) -> Unit) {
    val colors = mapOf(
        "Y" to Color(0xFFFBBF24),
        "X" to Color(0xFF60A5FA),
        "B" to Color(0xFFF97316),
        "A" to Color(0xFF34D399),
    )
    Box(modifier = Modifier.fillMaxSize()) {
        listOf(
            Triple("Y", Alignment.TopCenter, Modifier),
            Triple("X", Alignment.CenterStart, Modifier),
            Triple("B", Alignment.CenterEnd, Modifier),
            Triple("A", Alignment.BottomCenter, Modifier),
        ).forEach { (label, alignment, extraModifier) ->
            Surface(
                modifier = extraModifier
                    .align(alignment)
                    .size(46.dp)
                    .pointerInput(label) {
                        detectTapGestures(onPress = {
                            onButton(label, true)
                            tryAwaitRelease()
                            onButton(label, false)
                        })
                    },
                shape = CircleShape,
                color = colors.getValue(label).copy(alpha = 0.25f),
                border = androidx.compose.foundation.BorderStroke(1.5.dp, colors.getValue(label).copy(alpha = 0.82f)),
            ) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(label, color = Color.White, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
fun RuntimeDpad(
    element: LayoutElement,
    onDirection: (String, Boolean) -> Unit,
) {
    val fill = element.fillColor.asGamepadColor(element.alpha)
    val stroke = element.strokeColor.asGamepadColor()
    Box(modifier = Modifier.fillMaxSize()) {
        DpadButton(Modifier.align(Alignment.TopCenter), "UP", fill, stroke, onDirection)
        DpadButton(Modifier.align(Alignment.CenterStart), "LEFT", fill, stroke, onDirection)
        DpadButton(Modifier.align(Alignment.CenterEnd), "RIGHT", fill, stroke, onDirection)
        DpadButton(Modifier.align(Alignment.BottomCenter), "DOWN", fill, stroke, onDirection)
        Canvas(modifier = Modifier.fillMaxSize()) {
            drawCircle(
                color = fill.copy(alpha = 0.2f),
                radius = min(size.width, size.height) * 0.14f,
                center = Offset(size.width / 2f, size.height / 2f),
            )
        }
    }
}

@Composable
private fun DpadButton(
    modifier: Modifier,
    label: String,
    fill: Color,
    stroke: Color,
    onDirection: (String, Boolean) -> Unit,
) {
    Surface(
        modifier = modifier
            .size(46.dp)
            .pointerInput(label) {
                detectTapGestures(onPress = {
                    onDirection(label, true)
                    tryAwaitRelease()
                    onDirection(label, false)
                })
            },
        shape = RoundedCornerShape(16.dp),
        color = fill.copy(alpha = 0.22f),
        border = androidx.compose.foundation.BorderStroke(1.3.dp, stroke.copy(alpha = 0.66f)),
    ) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(label.take(1), color = Color.White, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun RuntimeJoystick(
    element: LayoutElement,
    onMove: (Float, Float) -> Unit,
) {
    var thumbOffset by remember(element.id) { mutableStateOf(Offset.Zero) }
    val outerFill = element.fillColor.asGamepadColor(element.alpha)
    val outerStroke = element.strokeColor.asGamepadColor().copy(alpha = 0.62f)

    Box(
        modifier = Modifier
            .fillMaxSize()
            .pointerInput(element.id, element.thumbRatio, element.deadZoneRatio) {
                fun update(position: Offset) {
                    val center = Offset(size.width / 2f, size.height / 2f)
                    val outerRadius = min(size.width, size.height) / 2f
                    val thumbRadius = (outerRadius * element.thumbRatio.coerceIn(0.18f, 0.7f) * 0.5f).coerceAtLeast(12f)
                    val travelRadius = (outerRadius - thumbRadius).coerceAtLeast(1f)
                    val deadZone = element.deadZoneRatio.coerceIn(0.02f, 0.35f)
                    val delta = position - center
                    val distance = delta.getDistance()
                    val clamped = if (distance > travelRadius) delta * (travelRadius / distance) else delta
                    val x = (clamped.x / travelRadius).coerceIn(-1f, 1f)
                    val y = (clamped.y / travelRadius).coerceIn(-1f, 1f)
                    thumbOffset = clamped
                    onMove(
                        if (abs(x) < deadZone) 0f else x,
                        if (abs(y) < deadZone) 0f else -y,
                    )
                }
                detectDragGestures(
                    onDragStart = { update(it) },
                    onDragEnd = {
                        thumbOffset = Offset.Zero
                        onMove(0f, 0f)
                    },
                    onDragCancel = {
                        thumbOffset = Offset.Zero
                        onMove(0f, 0f)
                    },
                ) { change, _ ->
                    update(change.position)
                    change.consume()
                }
            },
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val outerRadius = min(size.width, size.height) / 2f
            val thumbRadius = (outerRadius * element.thumbRatio.coerceIn(0.18f, 0.7f) * 0.5f).coerceAtLeast(12f)
            val deadZoneRadius = (outerRadius - thumbRadius) * element.deadZoneRatio.coerceIn(0.02f, 0.35f)

            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(outerFill.copy(alpha = outerFill.alpha * 0.34f), outerFill.copy(alpha = outerFill.alpha * 0.12f)),
                    center = center,
                    radius = outerRadius,
                ),
                radius = outerRadius,
                center = center,
            )
            drawCircle(color = outerStroke, radius = outerRadius, center = center, style = Stroke(width = 2.dp.toPx()))
            drawCircle(color = Color.White.copy(alpha = 0.15f), radius = outerRadius * 0.56f, center = center, style = Stroke(width = 1.dp.toPx()))
            drawCircle(color = outerStroke.copy(alpha = 0.18f), radius = deadZoneRadius, center = center, style = Stroke(width = 1.4.dp.toPx()))
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color.White.copy(alpha = 0.46f), outerFill.copy(alpha = 0.86f)),
                    center = center + thumbOffset,
                    radius = thumbRadius * 1.7f,
                ),
                radius = thumbRadius,
                center = center + thumbOffset,
            )
            drawCircle(color = Color.White.copy(alpha = 0.38f), radius = thumbRadius, center = center + thumbOffset, style = Stroke(width = 1.3.dp.toPx()))
        }
        if (element.labelVisible && !element.label.isNullOrBlank()) {
            Text(
                text = element.label.orEmpty(),
                modifier = Modifier.align(Alignment.Center),
                color = element.labelColor.asGamepadColor().copy(alpha = 0.82f),
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}

private fun Long.asGamepadColor(alphaMultiplier: Float = 1f): Color {
    val argb = this and 0xFFFFFFFF
    val alpha = (((argb shr 24) and 0xFF) / 255f * alphaMultiplier).coerceIn(0f, 1f)
    val red = ((argb shr 16) and 0xFF) / 255f
    val green = ((argb shr 8) and 0xFF) / 255f
    val blue = (argb and 0xFF) / 255f
    return Color(red = red, green = green, blue = blue, alpha = alpha)
}
