package com.neuralnexusstudios.nexremote.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.model.GamepadLayoutConfig
import com.neuralnexusstudios.nexremote.core.model.LayoutElement
import com.neuralnexusstudios.nexremote.core.model.MacroStep
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar

@Composable
fun LayoutEditorDialog(
    initialLayout: GamepadLayoutConfig,
    onDismiss: () -> Unit,
    onSave: (GamepadLayoutConfig) -> Unit,
) {
    var layout by remember { mutableStateOf(initialLayout) }
    var selectedElementId by remember { mutableStateOf(layout.elements.firstOrNull()?.id) }
    var editingMacroFor by remember { mutableStateOf<LayoutElement?>(null) }

    val selectedElement = layout.elements.firstOrNull { it.id == selectedElementId }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false),
    ) {
        Surface(modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.fillMaxSize()) {
                AppTopBar(
                    title = "Edit Layout",
                    onBack = onDismiss,
                    actions = {
                        TextButton(onClick = { onSave(layout) }) {
                            Text("Save")
                        }
                    },
                )
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        OutlinedTextField(
                            value = layout.name,
                            onValueChange = { layout = layout.copy(name = it) },
                            label = { Text("Layout Name") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                    item {
                        Text("Mode", style = MaterialTheme.typography.titleMedium)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("xinput", "dinput", "android").forEach { mode ->
                                FilterChip(
                                    selected = layout.mode == mode,
                                    onClick = { layout = layout.copy(mode = mode) },
                                    label = { Text(mode) },
                                )
                            }
                        }
                    }
                    item {
                        Text("Orientation", style = MaterialTheme.typography.titleMedium)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("landscape", "portrait").forEach { orientation ->
                                FilterChip(
                                    selected = layout.orientation == orientation,
                                    onClick = { layout = layout.copy(orientation = orientation) },
                                    label = { Text(orientation) },
                                )
                            }
                        }
                    }
                    item {
                        SettingCheckbox("Gyro enabled", layout.gyroEnabled) { layout = layout.copy(gyroEnabled = it) }
                    }
                    item {
                        SettingCheckbox("Accelerometer enabled", layout.accelEnabled) { layout = layout.copy(accelEnabled = it) }
                    }
                    item {
                        SettingCheckbox("Layout haptics", layout.hapticFeedback) { layout = layout.copy(hapticFeedback = it) }
                    }
                    item {
                        Text("Add Controls", style = MaterialTheme.typography.titleMedium)
                    }
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            EditorAddButton("Button") {
                                val element = defaultElement("button")
                                layout = layout.copy(elements = layout.elements + element)
                                selectedElementId = element.id
                            }
                            EditorAddButton("Trigger") {
                                val element = defaultElement("trigger")
                                layout = layout.copy(elements = layout.elements + element)
                                selectedElementId = element.id
                            }
                            EditorAddButton("Macro") {
                                val element = defaultElement("macro")
                                layout = layout.copy(elements = layout.elements + element)
                                selectedElementId = element.id
                            }
                        }
                    }
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            EditorAddButton("Joystick") {
                                val element = defaultElement("joystick")
                                layout = layout.copy(elements = layout.elements + element)
                                selectedElementId = element.id
                            }
                            EditorAddButton("D-pad") {
                                val element = defaultElement("dpad")
                                layout = layout.copy(elements = layout.elements + element)
                                selectedElementId = element.id
                            }
                            EditorAddButton("Face") {
                                val element = defaultElement("face_buttons")
                                layout = layout.copy(elements = layout.elements + element)
                                selectedElementId = element.id
                            }
                        }
                    }
                    item {
                        Text("Elements", style = MaterialTheme.typography.titleMedium)
                    }
                    items(layout.elements, key = { it.id }) { element ->
                        Surface(
                            tonalElevation = if (selectedElementId == element.id) 3.dp else 0.dp,
                            shape = MaterialTheme.shapes.medium,
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(10.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                TextButton(onClick = { selectedElementId = element.id }) {
                                    Text("${element.type}: ${element.label ?: element.action ?: element.id}")
                                }
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    TextButton(onClick = {
                                        val copy = element.copy(id = "${element.id}_copy_${System.currentTimeMillis()}")
                                        layout = layout.copy(elements = layout.elements + copy)
                                        selectedElementId = copy.id
                                    }) {
                                        Text("Duplicate")
                                    }
                                    TextButton(onClick = {
                                        layout = layout.copy(elements = layout.elements.filterNot { it.id == element.id })
                                        if (selectedElementId == element.id) {
                                            selectedElementId = layout.elements.firstOrNull()?.id
                                        }
                                    }) {
                                        Text("Delete")
                                    }
                                }
                            }
                        }
                    }
                    if (selectedElement != null) {
                        item {
                            Text("Selected Element", style = MaterialTheme.typography.titleMedium)
                        }
                        item {
                            ElementEditor(
                                element = selectedElement,
                                onChange = { updated ->
                                    layout = layout.copy(elements = layout.elements.map { if (it.id == updated.id) updated else it })
                                    selectedElementId = updated.id
                                },
                                onEditMacro = { editingMacroFor = it },
                            )
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
                val updated = element.copy(macro = steps)
                layout = layout.copy(elements = layout.elements.map { if (it.id == updated.id) updated else it })
                editingMacroFor = null
            },
        )
    }
}

@Composable
private fun SettingCheckbox(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Checkbox(checked = checked, onCheckedChange = onCheckedChange)
        Text(label, modifier = Modifier.padding(top = 12.dp))
    }
}

@Composable
private fun EditorAddButton(label: String, onClick: () -> Unit) {
    Button(onClick = onClick) {
        Text(label)
    }
}

@Composable
private fun ElementEditor(
    element: LayoutElement,
    onChange: (LayoutElement) -> Unit,
    onEditMacro: (LayoutElement) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(value = element.label.orEmpty(), onValueChange = { onChange(element.copy(label = it)) }, label = { Text("Label") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = element.action.orEmpty(), onValueChange = { onChange(element.copy(action = it)) }, label = { Text("Action") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = element.stick.orEmpty(), onValueChange = { onChange(element.copy(stick = it)) }, label = { Text("Stick") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = element.trigger.orEmpty(), onValueChange = { onChange(element.copy(trigger = it)) }, label = { Text("Trigger") }, modifier = Modifier.fillMaxWidth())
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumericField("X", element.x, Modifier.weight(1f)) { onChange(element.copy(x = it)) }
            NumericField("Y", element.y, Modifier.weight(1f)) { onChange(element.copy(y = it)) }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumericField("Width", element.width, Modifier.weight(1f)) { onChange(element.copy(width = it)) }
            NumericField("Height", element.height, Modifier.weight(1f)) { onChange(element.copy(height = it)) }
        }
        NumericField("Scale", element.scale, Modifier.fillMaxWidth()) { onChange(element.copy(scale = it)) }
        if (element.type == "macro") {
            Button(onClick = { onEditMacro(element) }) { Text("Edit Macro (${element.macro.size})") }
        }
    }
}

@Composable
private fun NumericField(
    label: String,
    value: Float,
    modifier: Modifier,
    onValue: (Float) -> Unit,
) {
    var text by remember(value) { mutableStateOf(value.toString()) }
    OutlinedTextField(
        value = text,
        onValueChange = {
            text = it
            it.toFloatOrNull()?.let(onValue)
        },
        label = { Text(label) },
        modifier = modifier,
    )
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

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Macro Steps") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                LazyColumn(modifier = Modifier.heightIn(max = 220.dp)) {
                    items(steps) { step ->
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${step.action} (+${step.delayMs}ms)")
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                TextButton(onClick = {
                                    val index = steps.indexOf(step)
                                    if (index > 0) {
                                        val updated = steps.toMutableList()
                                        updated.removeAt(index)
                                        updated.add(index - 1, step)
                                        steps = updated
                                    }
                                }) { Text("Up") }
                                TextButton(onClick = { steps = steps - step }) { Text("Delete") }
                            }
                        }
                    }
                }
                OutlinedTextField(value = action, onValueChange = { action = it }, label = { Text("Action") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = delay, onValueChange = { delay = it }, label = { Text("Delay ms") }, modifier = Modifier.fillMaxWidth())
                Button(onClick = {
                    steps = steps + MacroStep(action = action, delayMs = delay.toIntOrNull() ?: 0)
                    action = "button:A"
                    delay = "0"
                }) { Text("Add Step") }
            }
        },
        confirmButton = { Button(onClick = { onSave(steps) }) { Text("Save") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

private fun defaultElement(type: String): LayoutElement {
    val baseId = "${type}_${System.currentTimeMillis()}"
    return when (type) {
        "joystick" -> LayoutElement(baseId, type, 0.4f, 0.4f, 100f, 100f, stick = "left")
        "dpad" -> LayoutElement(baseId, type, 0.04f, 0.32f, 120f, 120f)
        "face_buttons" -> LayoutElement(baseId, type, 0.76f, 0.32f, 120f, 120f)
        "trigger" -> LayoutElement(baseId, type, 0.04f, 0.18f, 70f, 36f, label = "L2", trigger = "LT")
        "macro" -> LayoutElement(baseId, type, 0.45f, 0.45f, 80f, 46f, label = "Macro")
        else -> LayoutElement(baseId, type, 0.45f, 0.45f, 70f, 40f, label = "BTN", action = "A")
    }
}
