package com.neuralnexusstudios.nexremote.core.model

import kotlin.math.max
import kotlin.math.min

const val GAMEPAD_LAYOUT_VERSION = 2

private const val LEGACY_REFERENCE_SPAN = 420f

data class GamepadBindingOption(
    val label: String,
    val bindingType: String,
    val bindingValue: String,
)

data class GamepadBindingGroup(
    val label: String,
    val options: List<GamepadBindingOption>,
)

val GamepadBindingGroups: List<GamepadBindingGroup> = listOf(
    GamepadBindingGroup(
        label = "Controller Buttons",
        options = listOf(
            "A",
            "B",
            "X",
            "Y",
            "L1",
            "R1",
            "SELECT",
            "START",
            "GUIDE",
            "L3",
            "R3",
        ).map { GamepadBindingOption(it, "button", it) },
    ),
    GamepadBindingGroup(
        label = "Triggers",
        options = listOf(
            GamepadBindingOption("Left Trigger", "trigger", "LT"),
            GamepadBindingOption("Right Trigger", "trigger", "RT"),
        ),
    ),
    GamepadBindingGroup(
        label = "Joysticks",
        options = listOf(
            GamepadBindingOption("Left Stick", "stick", "left"),
            GamepadBindingOption("Right Stick", "stick", "right"),
        ),
    ),
    GamepadBindingGroup(
        label = "D-Pad",
        options = listOf(
            "UP",
            "DOWN",
            "LEFT",
            "RIGHT",
        ).map { GamepadBindingOption(it, "dpad", it) },
    ),
    GamepadBindingGroup(
        label = "Keyboard And Mouse",
        options = listOf(
            "mouse_left" to "Mouse Left",
            "mouse_right" to "Mouse Right",
            "keyboard_space" to "Space",
            "keyboard_ctrl" to "Ctrl",
            "keyboard_shift" to "Shift",
            "keyboard_tab" to "Tab",
            "keyboard_f" to "Use / F",
            "keyboard_r" to "Reload / R",
            "keyboard_q" to "Q",
            "keyboard_e" to "E",
            "keyboard_g" to "G",
            "keyboard_i" to "Inventory / I",
            "keyboard_v" to "Melee / V",
            "keyboard_z" to "Prone / Z",
            "keyboard_w" to "W",
            "keyboard_s" to "S",
        ).map { (value, label) -> GamepadBindingOption(label, "button", value) },
    ),
    GamepadBindingGroup(
        label = "Sensors",
        options = listOf(GamepadBindingOption("Gyro", "gyro", "gyro")),
    ),
)

val BuiltInGamepadLayoutIds: Set<String> = DefaultGamepadLayouts.builtIns.mapTo(linkedSetOf()) { it.id }

fun GamepadLayoutConfig.canvasFor(isLandscape: Boolean): GamepadCanvasConfig =
    if (isLandscape) landscapeCanvas else portraitCanvas

fun GamepadLayoutConfig.withCanvas(
    isLandscape: Boolean,
    canvas: GamepadCanvasConfig,
): GamepadLayoutConfig = if (isLandscape) {
    copy(landscapeCanvas = canvas, orientation = "landscape")
} else {
    copy(portraitCanvas = canvas, orientation = "portrait")
}

fun GamepadLayoutConfig.elementById(
    isLandscape: Boolean,
    elementId: String?,
): LayoutElement? = canvasFor(isLandscape).elements.firstOrNull { it.id == elementId }

fun GamepadLayoutConfig.replaceElement(
    isLandscape: Boolean,
    updated: LayoutElement,
): GamepadLayoutConfig {
    val currentCanvas = canvasFor(isLandscape)
    val nextElements = currentCanvas.elements.map { if (it.id == updated.id) updated else it }
    return withCanvas(isLandscape, currentCanvas.copy(elements = nextElements.sortedBy { it.zIndex }))
}

fun GamepadLayoutConfig.removeElement(
    isLandscape: Boolean,
    elementId: String,
): GamepadLayoutConfig {
    val currentCanvas = canvasFor(isLandscape)
    return withCanvas(isLandscape, currentCanvas.copy(elements = currentCanvas.elements.filterNot { it.id == elementId }))
}

fun GamepadLayoutConfig.appendElement(
    isLandscape: Boolean,
    element: LayoutElement,
): GamepadLayoutConfig {
    val currentCanvas = canvasFor(isLandscape)
    return withCanvas(isLandscape, currentCanvas.copy(elements = (currentCanvas.elements + element).sortedBy { it.zIndex }))
}

fun GamepadLayoutConfig.migrateLegacyLayout(): GamepadLayoutConfig {
    val portraitSource = when {
        portraitCanvas.elements.isNotEmpty() -> portraitCanvas
        elements.isNotEmpty() -> GamepadCanvasConfig(elements = elements)
        else -> portraitCanvas
    }
    val landscapeSource = when {
        landscapeCanvas.elements.isNotEmpty() -> landscapeCanvas
        elements.isNotEmpty() -> GamepadCanvasConfig(elements = elements)
        else -> landscapeCanvas
    }

    return copy(
        version = GAMEPAD_LAYOUT_VERSION,
        portraitCanvas = portraitSource.normalizeForOrientation(isLandscape = false).fitIntoCanvas(),
        landscapeCanvas = landscapeSource.normalizeForOrientation(isLandscape = true).fitIntoCanvas(),
        elements = emptyList(),
    )
}

fun GamepadLayoutConfig.normalizeForStorage(): GamepadLayoutConfig = migrateLegacyLayout().copy(elements = emptyList())

fun GamepadLayoutConfig.fitCurrentOrientation(isLandscape: Boolean): GamepadLayoutConfig =
    withCanvas(isLandscape, canvasFor(isLandscape).fitIntoCanvas())

fun GamepadLayoutConfig.fitBothOrientations(): GamepadLayoutConfig = copy(
    portraitCanvas = portraitCanvas.fitIntoCanvas(),
    landscapeCanvas = landscapeCanvas.fitIntoCanvas(),
)

fun GamepadLayoutConfig.centerSelection(
    isLandscape: Boolean,
    elementId: String?,
): GamepadLayoutConfig {
    val element = elementById(isLandscape, elementId) ?: return this
    val centered = element.withNormalizedFrame(
        centerX = 0.5f,
        centerY = 0.5f,
        widthRatio = normalizedWidth(element, isLandscape),
        heightRatio = normalizedHeight(element, isLandscape),
    )
    return replaceElement(isLandscape, centered).fitCurrentOrientation(isLandscape)
}

fun GamepadCanvasConfig.normalizeForOrientation(isLandscape: Boolean): GamepadCanvasConfig = copy(
    elements = elements.map { it.normalizeForOrientation(isLandscape) }.sortedBy { it.zIndex },
)

fun GamepadCanvasConfig.fitIntoCanvas(): GamepadCanvasConfig {
    val safePadding = safePaddingRatio.coerceIn(0.02f, 0.14f)
    val safeWidth = (1f - safePadding * 2f).coerceAtLeast(0.6f)
    val safeHeight = (1f - safePadding * 2f).coerceAtLeast(0.6f)

    val fitted = elements.map { element ->
        val normalized = element.normalizeForOrientation(isLandscape = true)
        val sizeRange = normalized.sizeRange()
        var width = normalizedWidth(normalized, true).coerceIn(sizeRange.minWidth, sizeRange.maxWidth)
        var height = normalizedHeight(normalized, true).coerceIn(sizeRange.minHeight, sizeRange.maxHeight)

        if (width > safeWidth || height > safeHeight) {
            val shrinkScale = min(safeWidth / width, safeHeight / height)
            width *= shrinkScale
            height *= shrinkScale
        }

        val minCenterX = safePadding + width / 2f
        val maxCenterX = 1f - safePadding - width / 2f
        val minCenterY = safePadding + height / 2f
        val maxCenterY = 1f - safePadding - height / 2f
        normalized.withNormalizedFrame(
            centerX = normalizedCenterX(normalized, true).coerceIn(minCenterX, maxCenterX.coerceAtLeast(minCenterX)),
            centerY = normalizedCenterY(normalized, true).coerceIn(minCenterY, maxCenterY.coerceAtLeast(minCenterY)),
            widthRatio = width,
            heightRatio = height,
        )
    }
    return copy(elements = fitted.sortedBy { it.zIndex })
}

fun LayoutElement.normalizeForOrientation(isLandscape: Boolean): LayoutElement {
    val widthRatio = normalizedWidth(this, isLandscape)
    val heightRatio = normalizedHeight(this, isLandscape)
    val centerX = normalizedCenterX(this, isLandscape, widthRatio)
    val centerY = normalizedCenterY(this, isLandscape, heightRatio)
    return copy(
        centerX = centerX.coerceIn(0f, 1f),
        centerY = centerY.coerceIn(0f, 1f),
        widthRatio = widthRatio,
        heightRatio = heightRatio,
        fillColor = fillColor.takeIf { it != 0L } ?: colorValue,
        strokeColor = strokeColor.takeIf { it != 0L } ?: 0xFFFFFFFF,
        labelColor = labelColor.takeIf { it != 0L } ?: 0xFFFFFFFF,
        alpha = alpha.coerceIn(0.2f, 1f),
        thumbRatio = thumbRatio.coerceIn(0.18f, 0.7f),
        deadZoneRatio = deadZoneRatio.coerceIn(0.02f, 0.35f),
        bindingType = resolveBindingType(this),
        bindingValue = resolveBindingValue(this),
        stylePreset = if (stylePreset.isBlank()) defaultStylePreset(type) else stylePreset,
        controlRole = controlRole.ifBlank { type },
    )
}

fun LayoutElement.withNormalizedFrame(
    centerX: Float = this.centerX,
    centerY: Float = this.centerY,
    widthRatio: Float = this.widthRatio,
    heightRatio: Float = this.heightRatio,
): LayoutElement = copy(
    centerX = centerX,
    centerY = centerY,
    widthRatio = widthRatio,
    heightRatio = heightRatio,
)

fun LayoutElement.createDuplicate(): LayoutElement = copy(
    id = "${id}_copy_${System.currentTimeMillis()}",
    centerX = (normalizedCenterX(this, true) + 0.03f).coerceAtMost(0.92f),
    centerY = (normalizedCenterY(this, true) + 0.03f).coerceAtMost(0.92f),
    zIndex = zIndex + 1,
)

fun createLayoutElement(
    type: String,
    isLandscape: Boolean,
    zIndex: Int = 0,
): LayoutElement {
    val (width, height) = when (type) {
        "joystick" -> if (isLandscape) 0.22f to 0.22f else 0.28f to 0.18f
        "dpad", "face_buttons" -> if (isLandscape) 0.18f to 0.18f else 0.22f to 0.14f
        "trigger" -> if (isLandscape) 0.14f to 0.08f else 0.18f to 0.07f
        "macro" -> 0.16f to 0.08f
        else -> 0.14f to 0.08f
    }
    return LayoutElement(
        id = "${type}_${System.currentTimeMillis()}",
        type = type,
        centerX = 0.5f,
        centerY = 0.5f,
        widthRatio = width,
        heightRatio = height,
        fillColor = defaultFillColor(type),
        strokeColor = defaultStrokeColor(type),
        labelColor = 0xFFFFFFFF,
        alpha = 0.92f,
        labelVisible = true,
        stylePreset = defaultStylePreset(type),
        controlRole = type,
        bindingType = when (type) {
            "trigger" -> "trigger"
            "joystick" -> "stick"
            "dpad" -> "dpad"
            "macro" -> "macro"
            "face_buttons" -> "cluster"
            else -> "button"
        },
        bindingValue = when (type) {
            "trigger" -> "LT"
            "joystick" -> "left"
            "face_buttons" -> "cluster"
            "macro" -> "macro"
            else -> "A"
        },
        thumbRatio = 0.42f,
        deadZoneRatio = 0.12f,
        label = when (type) {
            "joystick" -> "MOVE"
            "trigger" -> "L2"
            "macro" -> "MACRO"
            "utility" -> "USE"
            else -> "BTN"
        },
        action = when (type) {
            "button", "utility" -> "A"
            else -> null
        },
        stick = if (type == "joystick") "left" else null,
        trigger = if (type == "trigger") "LT" else null,
        zIndex = zIndex,
    )
}

fun LayoutElement.applyBinding(
    bindingType: String,
    bindingValue: String,
): LayoutElement = when (bindingType) {
    "trigger" -> copy(
        bindingType = bindingType,
        bindingValue = bindingValue,
        trigger = bindingValue,
        stick = null,
        action = null,
    )
    "stick" -> copy(
        bindingType = bindingType,
        bindingValue = bindingValue,
        stick = bindingValue,
        trigger = null,
        action = null,
    )
    "macro" -> copy(
        bindingType = bindingType,
        bindingValue = bindingValue,
        action = null,
        trigger = null,
        stick = null,
    )
    else -> copy(
        bindingType = bindingType,
        bindingValue = bindingValue,
        action = bindingValue,
        trigger = null,
        stick = null,
    )
}

fun bindingOptionsFor(type: String): List<GamepadBindingGroup> = when (type) {
    "joystick" -> GamepadBindingGroups.filter { it.label == "Joysticks" }
    "trigger" -> GamepadBindingGroups.filter { it.label == "Triggers" }
    "dpad" -> GamepadBindingGroups.filter { it.label == "D-Pad" }
    "macro" -> emptyList()
    "face_buttons" -> GamepadBindingGroups.filter { it.label == "Controller Buttons" }
    else -> GamepadBindingGroups.filterNot { it.label == "Joysticks" || it.label == "Triggers" || it.label == "D-Pad" || it.label == "Sensors" }
}

private fun LayoutElement.sizeRange(): ElementSizeRange = when (type) {
    "joystick" -> ElementSizeRange(0.16f, 0.14f, 0.4f, 0.34f)
    "dpad", "face_buttons" -> ElementSizeRange(0.12f, 0.12f, 0.3f, 0.26f)
    "trigger" -> ElementSizeRange(0.1f, 0.05f, 0.24f, 0.18f)
    "macro" -> ElementSizeRange(0.12f, 0.06f, 0.3f, 0.18f)
    else -> ElementSizeRange(0.08f, 0.05f, 0.26f, 0.24f)
}

private fun resolveBindingType(element: LayoutElement): String = when {
    element.bindingType.isNotBlank() -> element.bindingType
    !element.trigger.isNullOrBlank() -> "trigger"
    !element.stick.isNullOrBlank() -> "stick"
    element.type == "dpad" -> "dpad"
    element.type == "macro" -> "macro"
    element.type == "face_buttons" -> "cluster"
    else -> "button"
}

private fun resolveBindingValue(element: LayoutElement): String? = when {
    !element.bindingValue.isNullOrBlank() -> element.bindingValue
    !element.action.isNullOrBlank() -> element.action
    !element.trigger.isNullOrBlank() -> element.trigger
    !element.stick.isNullOrBlank() -> element.stick
    else -> null
}

private fun defaultStylePreset(type: String): String = when (type) {
    "joystick" -> "joystick"
    "trigger" -> "trigger"
    "dpad" -> "dpad"
    "face_buttons" -> "face_cluster"
    "utility" -> "utility"
    "macro" -> "macro"
    else -> "button"
}

private fun defaultFillColor(type: String): Long = when (type) {
    "joystick" -> 0x803B82F6
    "trigger" -> 0xCC1D4ED8
    "face_buttons" -> 0x00000000
    "dpad" -> 0x7F334155
    "utility" -> 0xAA111827
    "macro" -> 0xCC7C3AED
    else -> 0xCC374151
}

private fun defaultStrokeColor(type: String): Long = when (type) {
    "joystick" -> 0xFFE0F2FE
    "face_buttons" -> 0xFFFFFFFF
    "dpad" -> 0xFFD1D5DB
    else -> 0xFFFFFFFF
}

private fun normalizedCenterX(
    element: LayoutElement,
    isLandscape: Boolean,
    widthRatio: Float = normalizedWidth(element, isLandscape),
): Float = when {
    element.centerX >= 0f -> element.centerX
    element.x >= 0f -> (element.x + widthRatio / 2f)
    else -> 0.5f
}

private fun normalizedCenterY(
    element: LayoutElement,
    isLandscape: Boolean,
    heightRatio: Float = normalizedHeight(element, isLandscape),
): Float = when {
    element.centerY >= 0f -> element.centerY
    element.y >= 0f -> (element.y + heightRatio / 2f)
    else -> 0.5f
}

private fun normalizedWidth(
    element: LayoutElement,
    isLandscape: Boolean,
): Float = when {
    element.widthRatio > 0f -> element.widthRatio
    element.width > 0f -> (element.width / LEGACY_REFERENCE_SPAN).coerceIn(0.08f, if (isLandscape) 0.38f else 0.44f)
    else -> createLayoutElement(element.type, isLandscape).widthRatio
}

private fun normalizedHeight(
    element: LayoutElement,
    isLandscape: Boolean,
): Float = when {
    element.heightRatio > 0f -> element.heightRatio
    element.height > 0f -> (element.height / LEGACY_REFERENCE_SPAN).coerceIn(0.05f, if (isLandscape) 0.34f else 0.4f)
    else -> createLayoutElement(element.type, isLandscape).heightRatio
}

private data class ElementSizeRange(
    val minWidth: Float,
    val minHeight: Float,
    val maxWidth: Float,
    val maxHeight: Float,
)

