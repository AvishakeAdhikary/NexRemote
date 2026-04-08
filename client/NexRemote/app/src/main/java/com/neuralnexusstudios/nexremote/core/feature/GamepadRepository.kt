package com.neuralnexusstudios.nexremote.core.feature

import com.neuralnexusstudios.nexremote.core.model.DefaultGamepadLayouts
import com.neuralnexusstudios.nexremote.core.model.GamepadLayoutConfig
import com.neuralnexusstudios.nexremote.core.model.MacroStep
import com.neuralnexusstudios.nexremote.core.model.normalizeForStorage
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nexremote.core.storage.AppPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class GamepadRepository(
    private val preferences: AppPreferences,
    private val connectionRepository: NexRemoteConnectionRepository,
) {
    private val _layouts = MutableStateFlow<List<GamepadLayoutConfig>>(emptyList())
    private val _activeLayout = MutableStateFlow(DefaultGamepadLayouts.builtIns.first())

    val layouts: StateFlow<List<GamepadLayoutConfig>> = _layouts
    val activeLayout: StateFlow<GamepadLayoutConfig> = _activeLayout

    init {
        reload()
    }

    fun reload() {
        val (layouts, activeId) = preferences.loadLayouts()
        _layouts.value = layouts
        _activeLayout.value = layouts.firstOrNull { it.id == activeId } ?: layouts.first()
    }

    fun setActive(layout: GamepadLayoutConfig) {
        val normalized = layout.normalizeForStorage()
        val updated = _layouts.value.map { if (it.id == normalized.id) normalized else it }
        _layouts.value = updated
        preferences.saveLayouts(updated, normalized.id)
        _activeLayout.value = normalized
        sendModeChange(normalized.mode)
    }

    fun saveLayout(layout: GamepadLayoutConfig) {
        val normalized = layout.normalizeForStorage()
        val updated = _layouts.value.toMutableList()
        val index = updated.indexOfFirst { it.id == normalized.id }
        if (index >= 0) updated[index] = normalized else updated += normalized
        _layouts.value = updated
        if (_activeLayout.value.id == normalized.id) {
            _activeLayout.value = normalized
        }
        preferences.saveLayouts(updated, _activeLayout.value.id)
    }

    fun deleteLayout(layoutId: String) {
        val updated = _layouts.value.filterNot { it.id == layoutId }
        val nextActive = if (_activeLayout.value.id == layoutId) updated.firstOrNull() ?: DefaultGamepadLayouts.builtIns.first() else _activeLayout.value
        _layouts.value = updated
        _activeLayout.value = nextActive
        preferences.saveLayouts(updated, nextActive.id)
    }

    fun sendButton(button: String, pressed: Boolean) {
        connectionRepository.sendMessage(
            mapOf(
                "type" to currentModeType(),
                "input_type" to "button",
                "button" to button,
                "pressed" to pressed,
            ),
        )
    }

    fun sendDpad(direction: String, pressed: Boolean) {
        connectionRepository.sendMessage(
            mapOf(
                "type" to currentModeType(),
                "input_type" to "dpad",
                "direction" to direction.lowercase(),
                "pressed" to pressed,
            ),
        )
    }

    fun sendJoystick(stick: String, x: Float, y: Float) {
        connectionRepository.sendMessage(
            mapOf(
                "type" to currentModeType(),
                "input_type" to "joystick",
                "stick" to stick,
                "x" to x,
                "y" to y,
            ),
        )
    }

    fun sendTrigger(trigger: String, value: Float) {
        connectionRepository.sendMessage(
            mapOf(
                "type" to currentModeType(),
                "input_type" to "trigger",
                "trigger" to trigger,
                "value" to value,
            ),
        )
    }

    fun sendGyro(x: Float, y: Float, z: Float) {
        connectionRepository.sendMessage(
            mapOf(
                "type" to currentModeType(),
                "input_type" to "gyro",
                "x" to x,
                "y" to y,
                "z" to z,
            ),
        )
    }

    fun fireMacro(steps: List<MacroStep>) {
        connectionRepository.sendMessage(
            mapOf(
                "type" to "macro",
                "steps" to steps.map { mapOf("action" to it.action, "delay" to it.delayMs) },
            ),
        )
    }

    private fun currentModeType(): String = when (_activeLayout.value.mode) {
        "dinput" -> "gamepad_dinput"
        "android" -> "gamepad_android"
        else -> "gamepad"
    }

    private fun sendModeChange(mode: String) {
        if (mode != "android") {
            connectionRepository.sendMessage(mapOf("type" to "gamepad_mode", "mode" to mode))
        }
    }
}
