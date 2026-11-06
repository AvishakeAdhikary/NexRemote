package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.Canvas
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalConfiguration
import com.composeunstyled.ProvideContentColor
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxButton
import com.neuralnexusstudios.nex_remote.ui.design.NxChip
import com.neuralnexusstudios.nex_remote.ui.design.NxIconButton
import com.neuralnexusstudios.nex_remote.ui.design.NxSectionLabel
import com.neuralnexusstudios.nex_remote.ui.design.NxSwitchRow
import com.neuralnexusstudios.nex_remote.ui.design.NxTopBar
import com.neuralnexusstudios.nex_remote.ui.design.NxType
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import com.neuralnexusstudios.nex_remote.ui.design.compat.Button
import com.composables.ui.components.Checkbox
import com.neuralnexusstudios.nex_remote.ui.design.compat.FilterChip
import com.neuralnexusstudios.nex_remote.ui.design.compat.MaterialTheme
import com.neuralnexusstudios.nex_remote.ui.design.compat.OutlinedTextField
import com.composables.ui.components.Slider
import com.neuralnexusstudios.nex_remote.ui.design.compat.Surface
import com.composables.ui.components.Text
import com.neuralnexusstudios.nex_remote.ui.design.compat.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.neuralnexusstudios.nex_remote.core.model.GamepadBindingGroup
import com.neuralnexusstudios.nex_remote.core.model.GamepadLayoutConfig
import com.neuralnexusstudios.nex_remote.core.model.LayoutElement
import com.neuralnexusstudios.nex_remote.core.model.MacroStep
import com.neuralnexusstudios.nex_remote.core.model.appendElement
import com.neuralnexusstudios.nex_remote.core.model.applyBinding
import com.neuralnexusstudios.nex_remote.core.model.bindingOptionsFor
import com.neuralnexusstudios.nex_remote.core.model.canvasFor
import com.neuralnexusstudios.nex_remote.core.model.centerSelection
import com.neuralnexusstudios.nex_remote.core.model.createLayoutElement
import com.neuralnexusstudios.nex_remote.core.model.createDuplicate
import com.neuralnexusstudios.nex_remote.core.model.elementById
import com.neuralnexusstudios.nex_remote.core.model.fitBothOrientations
import com.neuralnexusstudios.nex_remote.core.model.fitCurrentOrientation
import com.neuralnexusstudios.nex_remote.core.model.normalizeForOrientation
import com.neuralnexusstudios.nex_remote.core.model.normalizeForStorage
import com.neuralnexusstudios.nex_remote.core.model.removeElement
import com.neuralnexusstudios.nex_remote.core.model.replaceElement
import com.neuralnexusstudios.nex_remote.core.model.withCanvas
import kotlin.math.roundToInt

private enum class EditorPanel { Tools, Properties }

/**
 * Full-screen layout editor, shown by GamepadScreen in place of the play view. The frame (top bar,
 * 12 dp padding, chip row, canvas with the same gradient and inset) mirrors GamepadScreen exactly, so
 * the canvas here has the same size and aspect as the one you play on. Tools and properties open in
 * a bottom panel over the canvas instead of shrinking it.
 */
@Composable
fun LayoutEditorDialog(
    initialLayout: GamepadLayoutConfig,
    onDismiss: () -> Unit,
    onSave: (GamepadLayoutConfig) -> Unit,
) {
    val baseLayout = remember(initialLayout.id) { initialLayout.normalizeForStorage() }
    var draftLayout by remember(initialLayout.id) { mutableStateOf(baseLayout.fitBothOrientations()) }
    // Start on the orientation the phone is in now, so the editor shows the canvas you just played on.
    val deviceLandscape = LocalConfiguration.current.orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE
    var isLandscape by remember(initialLayout.id) { mutableStateOf(deviceLandscape) }
    var selectedElementId by remember(initialLayout.id) { mutableStateOf(draftLayout.canvasFor(isLandscape).elements.firstOrNull()?.id) }
    var editingMacroFor by remember { mutableStateOf<LayoutElement?>(null) }
    var panel by remember { mutableStateOf<EditorPanel?>(null) }

    val currentCanvas = draftLayout.canvasFor(isLandscape)
    val selectedElement = draftLayout.elementById(isLandscape, selectedElementId)

    BackHandler { if (panel != null) panel = null else onDismiss() }

    val chips: @Composable RowScope.() -> Unit = {
        NxChip("Landscape", selected = isLandscape, onClick = {
            isLandscape = true
            draftLayout = draftLayout.fitCurrentOrientation(true)
            selectedElementId = draftLayout.canvasFor(true).elements.firstOrNull()?.id
        })
        NxChip("Portrait", selected = !isLandscape, onClick = {
            isLandscape = false
            draftLayout = draftLayout.fitCurrentOrientation(false)
            selectedElementId = draftLayout.canvasFor(false).elements.firstOrNull()?.id
        })
        NxChip("Add & tools", selected = panel == EditorPanel.Tools, icon = Icons.Outlined.Add, onClick = {
            panel = if (panel == EditorPanel.Tools) null else EditorPanel.Tools
        })
        NxChip("Properties", selected = panel == EditorPanel.Properties, icon = Icons.Outlined.Tune, onClick = {
            panel = if (panel == EditorPanel.Properties) null else EditorPanel.Properties
        })
    }
    val saveButton: @Composable () -> Unit = {
        NxButton("Save", onClick = { onSave(draftLayout.normalizeForStorage()) }, small = true, icon = Icons.Outlined.Check)
    }
    val editorCanvas: @Composable (Modifier) -> Unit = { modifier ->
        EditorCanvas(
            modifier = modifier,
            layout = draftLayout,
            isLandscape = isLandscape,
            selectedElementId = selectedElementId,
            onSelect = { selectedElementId = it },
            onTransform = { elementId, panX, panY, zoom ->
                val current = draftLayout.elementById(isLandscape, elementId) ?: return@EditorCanvas
                val nextWidth = (current.widthRatio * zoom).coerceIn(0.06f, 0.44f)
                val nextHeight = if (current.type in RoundPadTypes && !current.advancedSizing) {
                    (current.heightRatio * zoom).coerceIn(0.06f, 0.44f)
                } else {
                    (current.heightRatio * zoom).coerceIn(0.04f, 0.44f)
                }
                val grid = if (currentCanvas.snapToGrid) 0.02f else 0f
                val next = current.copy(
                    centerX = snapToGrid(current.centerX + panX, grid),
                    centerY = snapToGrid(current.centerY + panY, grid),
                    widthRatio = snapToGrid(nextWidth, grid.takeIf { it > 0f } ?: 0f),
                    heightRatio = snapToGrid(nextHeight, grid.takeIf { it > 0f } ?: 0f),
                )
                draftLayout = draftLayout.replaceElement(isLandscape, next).fitCurrentOrientation(isLandscape)
            },
        )
    }

    Box(Modifier.fillMaxSize().background(Nx.background)) {
        ProvideContentColor(Nx.onBackground) {
            if (deviceLandscape) {
                // Same frame as the landscape play screen, so the canvas is identical.
                GamepadLandscapeFrame(
                    title = "Edit layout",
                    onBack = onDismiss,
                    actions = {
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) { chips() }
                        saveButton()
                    },
                    canvas = editorCanvas,
                )
            } else {
                Column(Modifier.fillMaxSize()) {
                    NxTopBar(title = "Edit layout", onBack = onDismiss, actions = { saveButton() })
                    Column(
                        modifier = Modifier.fillMaxWidth().weight(1f).padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            content = chips,
                        )
                        editorCanvas(Modifier.weight(1f).fillMaxWidth())
                    }
                    Box(Modifier.windowInsetsPadding(WindowInsets.navigationBars))
                }
            }

            AnimatedVisibility(
                visible = panel != null,
                modifier = Modifier.align(Alignment.BottomCenter),
                enter = slideInVertically { it } + fadeIn(),
                exit = slideOutVertically { it } + fadeOut(),
            ) {
                BoxWithConstraints {
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .heightIn(max = maxHeight * 0.55f)
                            .clip(RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
                            .background(Nx.panel)
                            .border(1.dp, Nx.border, RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
                            .windowInsetsPadding(WindowInsets.navigationBars),
                    ) {
                        Row(
                            Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                if (panel == EditorPanel.Tools) "Add & tools" else selectedElement?.let { "Properties · ${it.label ?: it.type}" } ?: "Properties",
                                style = NxType.title,
                                modifier = Modifier.weight(1f),
                            )
                            NxIconButton(Icons.Outlined.Close, contentDescription = "Close panel", onClick = { panel = null })
                        }
                        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState())) {
                            when (panel) {
                                EditorPanel.Tools -> EditorToolbar(
                                    selectedElement = selectedElement,
                                    onAdd = { type ->
                                        val element = createLayoutElement(type, isLandscape, currentCanvas.elements.size)
                                        draftLayout = draftLayout.appendElement(isLandscape, element).fitCurrentOrientation(isLandscape)
                                        selectedElementId = element.id
                                        panel = null
                                    },
                                    onDuplicate = {
                                        selectedElement?.let {
                                            val duplicate = it.createDuplicate()
                                            draftLayout = draftLayout.appendElement(isLandscape, duplicate).fitCurrentOrientation(isLandscape)
                                            selectedElementId = duplicate.id
                                        }
                                    },
                                    onDelete = {
                                        selectedElementId?.let {
                                            draftLayout = draftLayout.removeElement(isLandscape, it)
                                            selectedElementId = draftLayout.canvasFor(isLandscape).elements.firstOrNull()?.id
                                        }
                                    },
                                    onFitCurrent = { draftLayout = draftLayout.fitCurrentOrientation(isLandscape) },
                                    onFitBoth = { draftLayout = draftLayout.fitBothOrientations() },
                                    onCenter = {
                                        draftLayout = draftLayout.centerSelection(isLandscape, selectedElementId).fitCurrentOrientation(isLandscape)
                                    },
                                    onResetOrientation = {
                                        draftLayout = draftLayout.withCanvas(isLandscape, baseLayout.canvasFor(isLandscape)).fitCurrentOrientation(isLandscape)
                                        selectedElementId = draftLayout.canvasFor(isLandscape).elements.firstOrNull()?.id
                                    },
                                    onDiscard = onDismiss,
                                )
                                EditorPanel.Properties -> EditorPropertiesPanel(
                                    layout = draftLayout,
                                    selectedElement = selectedElement,
                                    isLandscape = isLandscape,
                                    onLayoutChange = { draftLayout = it },
                                    onElementChange = { draftLayout = draftLayout.replaceElement(isLandscape, it).fitCurrentOrientation(isLandscape) },
                                    onEditMacro = { editingMacroFor = it },
                                )
                                null -> Unit
                            }
                        }
                    }
                }
            }
        }
    }

    editingMacroFor?.let { element ->
        MacroEditorDialog(
            initialSteps = element.macro,
            onDismiss = { editingMacroFor = null },
            onSave = { steps ->
                draftLayout = draftLayout.replaceElement(isLandscape, element.copy(macro = steps))
                editingMacroFor = null
            },
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EditorToolbar(
    selectedElement: LayoutElement?,
    onAdd: (String) -> Unit,
    onDuplicate: () -> Unit,
    onDelete: () -> Unit,
    onFitCurrent: () -> Unit,
    onFitBoth: () -> Unit,
    onCenter: () -> Unit,
    onResetOrientation: () -> Unit,
    onDiscard: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, bottom = 20.dp, top = 4.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        NxSectionLabel("Add a control")
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(
                "button" to "Button",
                "utility" to "Utility",
                "trigger" to "Trigger",
                "macro" to "Macro",
                "joystick" to "Joystick",
                "dpad" to "D-pad",
                "face_buttons" to "Face buttons",
            ).forEach { (type, label) ->
                NxChip(label, selected = false, icon = Icons.Outlined.Add, onClick = { onAdd(type) })
            }
        }
        NxSectionLabel("Selected control")
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            NxChip("Duplicate", selected = false, enabled = selectedElement != null, onClick = onDuplicate)
            NxChip("Center", selected = false, enabled = selectedElement != null, onClick = onCenter)
            NxChip("Delete", selected = false, enabled = selectedElement != null, onClick = onDelete)
        }
        NxSectionLabel("Layout")
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            NxChip("Fit this orientation", selected = false, onClick = onFitCurrent)
            NxChip("Fit both", selected = false, onClick = onFitBoth)
            NxChip("Reset orientation", selected = false, onClick = onResetOrientation)
            NxChip("Discard changes", selected = false, onClick = onDiscard)
        }
    }
}

@Composable
private fun EditorCanvas(
    modifier: Modifier = Modifier,
    layout: GamepadLayoutConfig,
    isLandscape: Boolean,
    selectedElementId: String?,
    onSelect: (String) -> Unit,
    onTransform: (String, Float, Float, Float) -> Unit,
) {
    // Same surface as GamepadScreen (GamepadCanvasBox); elements laid out in the same 12 dp inset.
    GamepadCanvasBox(modifier) {
        BoxWithConstraints(Modifier.fillMaxSize().padding(12.dp)) {
            val canvas = layout.canvasFor(isLandscape)
            val canvasWidthPx = constraints.maxWidth.toFloat().coerceAtLeast(1f)
            val canvasHeightPx = constraints.maxHeight.toFloat().coerceAtLeast(1f)

            Canvas(modifier = Modifier.fillMaxSize()) {
                val safeX = size.width * canvas.safePaddingRatio
                val safeY = size.height * canvas.safePaddingRatio
                if (canvas.showSafeZones) {
                    drawRoundRect(
                        color = Color.White.copy(alpha = 0.12f),
                        topLeft = Offset(safeX, safeY),
                        size = Size(size.width - safeX * 2f, size.height - safeY * 2f),
                        style = Stroke(width = 2.dp.toPx()),
                        cornerRadius = androidx.compose.ui.geometry.CornerRadius(28.dp.toPx(), 28.dp.toPx()),
                    )
                }
                if (canvas.snapToGrid) {
                    val columns = 10
                    val rows = 10
                    repeat(columns - 1) { index ->
                        val x = size.width / columns * (index + 1)
                        drawLine(Color.White.copy(alpha = 0.05f), Offset(x, 0f), Offset(x, size.height))
                    }
                    repeat(rows - 1) { index ->
                        val y = size.height / rows * (index + 1)
                        drawLine(Color.White.copy(alpha = 0.05f), Offset(0f, y), Offset(size.width, y))
                    }
                }
            }

            canvas.elements.sortedBy { it.zIndex }.forEach { element ->
                val normalized = element.normalizeForOrientation(isLandscape)
                val bounds = padBounds(normalized, maxWidth, maxHeight)
                val isSelected = selectedElementId == element.id
                Box(
                    modifier = Modifier
                        .offset(x = bounds.left, y = bounds.top)
                        .size(width = bounds.width, height = bounds.height)
                        .border(
                            width = if (isSelected) 2.dp else 1.dp,
                            color = if (isSelected) Nx.primary else Color.White.copy(alpha = 0.2f),
                            shape = RoundedCornerShape(if (element.type in RoundPadTypes) 999.dp else 20.dp),
                        )
                        .pointerInput(element.id, isSelected, canvasWidthPx, canvasHeightPx) {
                            detectTransformGestures { _, pan, zoom, _ ->
                                onSelect(element.id)
                                if (element.locked) return@detectTransformGestures
                                onTransform(element.id, pan.x / canvasWidthPx, pan.y / canvasHeightPx, zoom)
                            }
                        }
                        .pointerInput(element.id) { detectTapGestures { onSelect(element.id) } },
                ) {
                    EditorElementPreview(element = normalized, isSelected = isSelected)
                }
            }
        }
    }
}

@Composable
private fun EditorElementPreview(
    element: LayoutElement,
    isSelected: Boolean,
) {
    val fill = element.fillColor.asEditorColor(element.alpha.coerceIn(0.2f, 1f))
    val stroke = element.strokeColor.asEditorColor(if (isSelected) 0.92f else 0.62f)
    Surface(
        modifier = Modifier.fillMaxSize().padding(4.dp),
        color = Color.Transparent,
        shape = RoundedCornerShape(if (element.type == "joystick" || element.type == "face_buttons") 999.dp else 18.dp),
        border = androidx.compose.foundation.BorderStroke(1.2.dp, stroke),
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Brush.radialGradient(listOf(fill.copy(alpha = fill.alpha * 0.9f), fill.copy(alpha = fill.alpha * 0.35f)))),
            contentAlignment = Alignment.Center,
        ) {
            when (element.type) {
                "joystick" -> Canvas(modifier = Modifier.fillMaxSize()) {
                    val outerRadius = size.minDimension / 2f
                    val thumbRadius = outerRadius * element.thumbRatio.coerceIn(0.18f, 0.7f) * 0.5f
                    drawCircle(color = Color.White.copy(alpha = 0.18f), radius = outerRadius * 0.56f, center = center, style = Stroke(width = 1.dp.toPx()))
                    drawCircle(color = stroke, radius = outerRadius, center = center, style = Stroke(width = 1.8.dp.toPx()))
                    drawCircle(color = Color.White.copy(alpha = 0.46f), radius = thumbRadius, center = center)
                }
                "face_buttons" -> RuntimeFaceButtons(onButton = { _, _ -> })
                "dpad" -> RuntimeDpad(element = element, onDirection = { _, _ -> })
                else -> {
                    if (element.labelVisible) {
                        Text(
                            text = element.label ?: element.action ?: element.trigger ?: element.stick ?: element.type,
                            color = element.labelColor.asEditorColor(),
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun EditorPropertiesPanel(
    layout: GamepadLayoutConfig,
    selectedElement: LayoutElement?,
    isLandscape: Boolean,
    onLayoutChange: (GamepadLayoutConfig) -> Unit,
    onElementChange: (LayoutElement) -> Unit,
    onEditMacro: (LayoutElement) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 20.dp, end = 20.dp, bottom = 20.dp, top = 4.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        OutlinedTextField(
            value = layout.name,
            onValueChange = { onLayoutChange(layout.copy(name = it)) },
            label = { Text("Layout Name") },
            modifier = Modifier.fillMaxWidth(),
        )
        NxSwitchRow(
            title = "Vibrate on press",
            subtitle = "Feel a click when you press and release controls on this layout.",
            checked = layout.hapticFeedback,
            onCheckedChange = { onLayoutChange(layout.copy(hapticFeedback = it)) },
        )
        NxSwitchRow(
            title = "Gyroscope aiming",
            subtitle = "Tilt the phone to move the right stick.",
            checked = layout.gyroEnabled,
            onCheckedChange = { onLayoutChange(layout.copy(gyroEnabled = it)) },
        )
        NxSwitchRow(
            title = "Accelerometer",
            subtitle = "Use tilt from the accelerometer when there is no gyroscope.",
            checked = layout.accelEnabled,
            onCheckedChange = { onLayoutChange(layout.copy(accelEnabled = it)) },
        )
        Text("Canvas", style = MaterialTheme.typography.titleSmall)
        SliderField("Background Dim", layout.canvasFor(isLandscape).backgroundDim, 0f..0.45f) { value ->
            onLayoutChange(layout.withCanvas(isLandscape, layout.canvasFor(isLandscape).copy(backgroundDim = value)))
        }
        SettingCheckbox("Snap To Grid", layout.canvasFor(isLandscape).snapToGrid) { enabled ->
            onLayoutChange(layout.withCanvas(isLandscape, layout.canvasFor(isLandscape).copy(snapToGrid = enabled)))
        }
        SettingCheckbox("Show Safe Zones", layout.canvasFor(isLandscape).showSafeZones) { enabled ->
            onLayoutChange(layout.withCanvas(isLandscape, layout.canvasFor(isLandscape).copy(showSafeZones = enabled)))
        }

        selectedElement?.let { element ->
            Text("Selected control", style = MaterialTheme.typography.titleMedium)
            ElementProperties(
                element = element,
                onChange = onElementChange,
                onEditMacro = onEditMacro,
            )
        }
    }
}

@Composable
private fun ElementProperties(
    element: LayoutElement,
    onChange: (LayoutElement) -> Unit,
    onEditMacro: (LayoutElement) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        OutlinedTextField(
            value = element.label.orEmpty(),
            onValueChange = { onChange(element.copy(label = it)) },
            label = { Text("Label") },
            modifier = Modifier.fillMaxWidth(),
        )
        SettingCheckbox("Show Label", element.labelVisible) { onChange(element.copy(labelVisible = it)) }
        SettingCheckbox("Locked", element.locked) { onChange(element.copy(locked = it)) }
        SettingCheckbox("Advanced Sizing", element.advancedSizing) { onChange(element.copy(advancedSizing = it)) }
        SliderField("Opacity", element.alpha, 0.2f..1f) { onChange(element.copy(alpha = it)) }
        SliderField("Width Ratio", element.widthRatio, 0.06f..0.44f) { onChange(element.copy(widthRatio = it)) }
        SliderField("Height Ratio", element.heightRatio, 0.04f..0.44f) { onChange(element.copy(heightRatio = it)) }
        SliderField("Center X", element.centerX, 0f..1f) { onChange(element.copy(centerX = it)) }
        SliderField("Center Y", element.centerY, 0f..1f) { onChange(element.copy(centerY = it)) }

        if (element.type == "joystick") {
            SliderField("Thumb Size", element.thumbRatio, 0.18f..0.7f) { onChange(element.copy(thumbRatio = it)) }
            SliderField("Dead Zone", element.deadZoneRatio, 0.02f..0.35f) { onChange(element.copy(deadZoneRatio = it)) }
        }

        if (element.type == "macro") {
            Button(onClick = { onEditMacro(element) }) { Text("Edit Macro (${element.macro.size})") }
        } else if (element.type != "face_buttons") {
            BindingGroupSelector(
                groups = bindingOptionsFor(element.type),
                element = element,
                onChange = onChange,
            )
        }

        Text("Colors", style = MaterialTheme.typography.titleSmall)
        ColorPresetRow(
            onSelect = { color ->
                onChange(element.copy(fillColor = color, colorValue = color))
            },
        )
        ColorEditor("Fill", element.fillColor) { onChange(element.copy(fillColor = it, colorValue = it)) }
        ColorEditor("Border", element.strokeColor) { onChange(element.copy(strokeColor = it)) }
        ColorEditor("Label", element.labelColor) { onChange(element.copy(labelColor = it)) }
    }
}

@Composable
private fun BindingGroupSelector(
    groups: List<GamepadBindingGroup>,
    element: LayoutElement,
    onChange: (LayoutElement) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        groups.forEach { group ->
            Text(group.label, style = MaterialTheme.typography.labelLarge)
            Row(
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                group.options.forEach { option ->
                    FilterChip(
                        selected = element.bindingValue == option.bindingValue && element.bindingType == option.bindingType,
                        onClick = { onChange(element.applyBinding(option.bindingType, option.bindingValue)) },
                        label = { Text(option.label) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ColorPresetRow(
    onSelect: (Long) -> Unit,
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
        listOf(0xCC374151, 0xCC1D4ED8, 0xCCDC2626, 0xCC16A34A, 0xCC7C3AED, 0xCCCA8A04, 0xCC0F172A).forEach { value ->
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .background(value.asEditorColor(), CircleShape)
                    .border(1.dp, Color.White.copy(alpha = 0.4f), CircleShape)
                    .pointerInput(value) { detectTapGestures(onTap = { onSelect(value) }) },
            )
        }
    }
}

@Composable
private fun ColorEditor(
    label: String,
    colorValue: Long,
    onChange: (Long) -> Unit,
) {
    val color = colorValue.asEditorColor()
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        SliderField("R", color.red, 0f..1f) { onChange(updateColorChannel(color, red = it)) }
        SliderField("G", color.green, 0f..1f) { onChange(updateColorChannel(color, green = it)) }
        SliderField("B", color.blue, 0f..1f) { onChange(updateColorChannel(color, blue = it)) }
        SliderField("A", color.alpha, 0f..1f) { onChange(updateColorChannel(color, alpha = it)) }
    }
}

@Composable
private fun SliderField(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    onValueChange: (Float) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("$label: ${"%.2f".format(value)}", style = MaterialTheme.typography.labelLarge)
        Slider(value = value.coerceIn(range.start, range.endInclusive), onValueChange = onValueChange, valueRange = range)
    }
}

@Composable
private fun SettingCheckbox(
    label: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = checked, onCheckedChange = onCheckedChange)
        Text(label)
    }
}

@Composable
private fun MacroEditorDialog(
    initialSteps: List<MacroStep>,
    onDismiss: () -> Unit,
    onSave: (List<MacroStep>) -> Unit,
) {
    var steps by remember { mutableStateOf(initialSteps) }
    var action by remember { mutableStateOf("button:A") }
    var delay by remember { mutableStateOf("0") }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(24.dp)) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Macro Steps", style = MaterialTheme.typography.titleMedium)
                LazyColumn(modifier = Modifier.heightIn(max = 220.dp)) {
                    items(steps) { step ->
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${step.action} (+${step.delayMs}ms)")
                            TextButton(onClick = { steps = steps - step }) { Text("Delete") }
                        }
                    }
                }
                OutlinedTextField(value = action, onValueChange = { action = it }, label = { Text("Action") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = delay, onValueChange = { delay = it }, label = { Text("Delay ms") }, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        steps = steps + MacroStep(action = action, delayMs = delay.toIntOrNull() ?: 0)
                        action = "button:A"
                        delay = "0"
                    }) { Text("Add Step") }
                    Spacer(modifier = Modifier.width(4.dp))
                    TextButton(onClick = { onSave(steps) }) { Text("Save") }
                    TextButton(onClick = onDismiss) { Text("Cancel") }
                }
            }
        }
    }
}

private fun updateColorChannel(
    color: Color,
    red: Float = color.red,
    green: Float = color.green,
    blue: Float = color.blue,
    alpha: Float = color.alpha,
): Long {
    return Color(red = red, green = green, blue = blue, alpha = alpha).toArgb().toLong() and 0xFFFFFFFF
}

private fun snapToGrid(value: Float, step: Float): Float {
    if (step <= 0f) return value.coerceIn(0f, 1f)
    return ((value / step).roundToInt() * step).coerceIn(0f, 1f)
}

private fun Long.asEditorColor(alphaOverride: Float? = null): Color {
    val argb = this and 0xFFFFFFFF
    val alpha = alphaOverride ?: (((argb shr 24) and 0xFF) / 255f)
    val red = ((argb shr 16) and 0xFF) / 255f
    val green = ((argb shr 8) and 0xFF) / 255f
    val blue = (argb and 0xFF) / 255f
    return Color(red = red, green = green, blue = blue, alpha = alpha.coerceIn(0f, 1f))
}
