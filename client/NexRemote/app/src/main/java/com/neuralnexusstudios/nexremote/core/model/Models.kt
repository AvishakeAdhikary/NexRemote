package com.neuralnexusstudios.nexremote.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

enum class ConnectionStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
}

@Serializable
data class ServerInfo(
    val name: String,
    val address: String,
    val port: Int,
    @SerialName("port_insecure") val portInsecure: Int,
    val id: String = "",
    val version: String = "1.0.0",
    @SerialName("cert_fingerprint") val certificateFingerprint: String? = null,
)

@Serializable
data class FeatureStatus(
    val supported: Boolean? = null,
    val available: Boolean? = null,
    val reason: String? = null,
    @SerialName("action_required") val actionRequired: String? = null,
)

@Serializable
data class ServerCapabilities(
    val keyboard: Boolean = true,
    val mouse: Boolean = true,
    val gamepad: Boolean = false,
    @SerialName("gamepad_available") val gamepadAvailable: Boolean = false,
    @SerialName("gamepad_mode") val gamepadMode: String = "xinput",
    @SerialName("gamepad_modes") val gamepadModes: List<String> = emptyList(),
    @SerialName("screen_streaming") val screenStreaming: Boolean = true,
    @SerialName("screen_audio_streaming") val screenAudioStreaming: Boolean = true,
    @SerialName("camera_streaming") val cameraStreaming: Boolean = true,
    @SerialName("file_transfer") val fileTransfer: Boolean = true,
    val clipboard: Boolean = false,
    @SerialName("multi_display") val multiDisplay: Boolean = true,
)

data class ServerSessionState(
    val serverName: String = "",
    val connected: Boolean = false,
    val capabilities: ServerCapabilities? = null,
    val featureStatus: Map<String, FeatureStatus> = emptyMap(),
)

data class AppSettings(
    val deviceId: String,
    val deviceName: String,
    val lastServer: String? = null,
    val autoConnect: Boolean = false,
    val gyroSensitivity: Float = 1f,
    val appHapticsEnabled: Boolean = true,
    val useSecureConnection: Boolean = true,
    val termsAccepted: Boolean = false,
    val termsAcceptedAt: String? = null,
    val cameraDisclosureAccepted: Boolean = false,
)

@Serializable
data class MacroStep(
    val action: String,
    val delayMs: Int = 0,
)

@Serializable
data class GamepadCanvasConfig(
    val elements: List<LayoutElement> = emptyList(),
    val backgroundDim: Float = 0.16f,
    val snapToGrid: Boolean = true,
    val showSafeZones: Boolean = true,
    val safePaddingRatio: Float = 0.04f,
)

@Serializable
data class LayoutElement(
    val id: String,
    val type: String,
    val centerX: Float = -1f,
    val centerY: Float = -1f,
    val widthRatio: Float = -1f,
    val heightRatio: Float = -1f,
    val x: Float = -1f,
    val y: Float = -1f,
    val width: Float = -1f,
    val height: Float = -1f,
    val scale: Float = 1f,
    val colorValue: Long = 0xFF374151,
    val fillColor: Long = colorValue,
    val strokeColor: Long = 0xFFFFFFFF,
    val labelColor: Long = 0xFFFFFFFF,
    val alpha: Float = 0.92f,
    val rotation: Float = 0f,
    val zIndex: Int = 0,
    val locked: Boolean = false,
    val labelVisible: Boolean = true,
    val iconName: String? = null,
    val stylePreset: String = "default",
    val controlRole: String = type,
    val bindingType: String = when (type) {
        "trigger" -> "trigger"
        "joystick" -> "stick"
        "dpad" -> "dpad"
        "face_buttons" -> "cluster"
        "macro" -> "macro"
        else -> "button"
    },
    val bindingValue: String? = null,
    val thumbRatio: Float = 0.4f,
    val deadZoneRatio: Float = 0.12f,
    val advancedSizing: Boolean = false,
    val label: String? = null,
    val action: String? = null,
    val stick: String? = null,
    val trigger: String? = null,
    val macro: List<MacroStep> = emptyList(),
)

@Serializable
data class GamepadLayoutConfig(
    val id: String,
    val name: String,
    val version: Int = 2,
    val layoutKind: String = "classic_controller",
    val orientation: String = "landscape",
    val gyroEnabled: Boolean = false,
    val accelEnabled: Boolean = false,
    val hapticFeedback: Boolean = true,
    val mode: String = "xinput",
    val elements: List<LayoutElement> = emptyList(),
    val portraitCanvas: GamepadCanvasConfig = GamepadCanvasConfig(),
    val landscapeCanvas: GamepadCanvasConfig = GamepadCanvasConfig(),
)

data class MediaState(
    val volume: Int = 50,
    val isMuted: Boolean = false,
    val isPlaying: Boolean = false,
    val hasMedia: Boolean = false,
    val title: String = "No Media Playing",
    val artist: String = "",
)

data class DisplayInfo(
    val index: Int,
    val name: String,
    val width: Int,
    val height: Int,
    val left: Int = 0,
    val top: Int = 0,
    val isPrimary: Boolean = false,
)

data class ScreenAudioFormat(
    val sampleRate: Int,
    val channels: Int,
    val encoding: String,
    val bytesPerSample: Int,
)

data class CameraInfo(
    val index: Int,
    val name: String,
)

data class FileItem(
    val name: String,
    val path: String,
    val isDirectory: Boolean,
    val size: Long? = null,
    val modified: String? = null,
)

data class FileProperties(
    val name: String,
    val path: String,
    val kind: String,
    val size: String,
    val modified: String,
    val created: String,
)

data class DriveInfo(
    val name: String,
    val path: String,
    val kind: String,
    val isReady: Boolean,
    val label: String? = null,
)

data class ProcessInfo(
    val name: String,
    val pid: Int,
    val cpu: Double,
    val memory: Long,
)

data class SystemInfo(
    val cpuUsage: Double = 0.0,
    val memoryUsage: Double = 0.0,
    val diskUsage: Double = 0.0,
)

object DefaultGamepadLayouts {
    val builtIns: List<GamepadLayoutConfig> = listOf(
        buildStandardGamepadLayout(),
        buildFpsLayout(),
        buildRacingLayout(),
        buildShooterHudLayout(),
    )
}

private fun buildStandardGamepadLayout(): GamepadLayoutConfig {
    val landscape = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "left_stick", type = "joystick", cx = 0.17f, cy = 0.68f, w = 0.22f, h = 0.22f, stick = "left", label = "MOVE", fill = 0x803B82F6, stroke = 0xFFBFDBFE),
            layoutElement(id = "right_stick", type = "joystick", cx = 0.79f, cy = 0.68f, w = 0.22f, h = 0.22f, stick = "right", label = "LOOK", fill = 0x80F59E0B, stroke = 0xFFFDE68A),
            layoutElement(id = "face_cluster", type = "face_buttons", cx = 0.84f, cy = 0.38f, w = 0.18f, h = 0.18f, fill = 0x00000000, stroke = 0xFFFFFFFF),
            layoutElement(id = "dpad", type = "dpad", cx = 0.14f, cy = 0.37f, w = 0.16f, h = 0.16f, fill = 0x7F334155, stroke = 0xFFD1D5DB),
            layoutElement(id = "l1", type = "button", cx = 0.13f, cy = 0.09f, w = 0.12f, h = 0.08f, label = "L1", action = "L1", fill = 0xAA334155),
            layoutElement(id = "l2", type = "trigger", cx = 0.13f, cy = 0.19f, w = 0.13f, h = 0.09f, label = "L2", trigger = "LT", fill = 0xAA1D4ED8),
            layoutElement(id = "r1", type = "button", cx = 0.87f, cy = 0.09f, w = 0.12f, h = 0.08f, label = "R1", action = "R1", fill = 0xAA334155),
            layoutElement(id = "r2", type = "trigger", cx = 0.87f, cy = 0.19f, w = 0.13f, h = 0.09f, label = "R2", trigger = "RT", fill = 0xAAD97706),
            layoutElement(id = "back", type = "button", cx = 0.43f, cy = 0.1f, w = 0.12f, h = 0.07f, label = "BACK", action = "SELECT", fill = 0xAA111827),
            layoutElement(id = "start", type = "button", cx = 0.57f, cy = 0.1f, w = 0.12f, h = 0.07f, label = "START", action = "START", fill = 0xAA111827),
        ),
    )
    val portrait = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "left_stick", type = "joystick", cx = 0.22f, cy = 0.78f, w = 0.28f, h = 0.16f, stick = "left", label = "MOVE", fill = 0x803B82F6, stroke = 0xFFBFDBFE),
            layoutElement(id = "right_stick", type = "joystick", cx = 0.78f, cy = 0.78f, w = 0.28f, h = 0.16f, stick = "right", label = "LOOK", fill = 0x80F59E0B, stroke = 0xFFFDE68A),
            layoutElement(id = "face_cluster", type = "face_buttons", cx = 0.8f, cy = 0.53f, w = 0.22f, h = 0.12f, fill = 0x00000000, stroke = 0xFFFFFFFF),
            layoutElement(id = "dpad", type = "dpad", cx = 0.19f, cy = 0.53f, w = 0.2f, h = 0.12f, fill = 0x7F334155, stroke = 0xFFD1D5DB),
            layoutElement(id = "l1", type = "button", cx = 0.17f, cy = 0.08f, w = 0.18f, h = 0.06f, label = "L1", action = "L1", fill = 0xAA334155),
            layoutElement(id = "l2", type = "trigger", cx = 0.17f, cy = 0.16f, w = 0.18f, h = 0.07f, label = "L2", trigger = "LT", fill = 0xAA1D4ED8),
            layoutElement(id = "r1", type = "button", cx = 0.83f, cy = 0.08f, w = 0.18f, h = 0.06f, label = "R1", action = "R1", fill = 0xAA334155),
            layoutElement(id = "r2", type = "trigger", cx = 0.83f, cy = 0.16f, w = 0.18f, h = 0.07f, label = "R2", trigger = "RT", fill = 0xAAD97706),
            layoutElement(id = "back", type = "button", cx = 0.42f, cy = 0.08f, w = 0.16f, h = 0.05f, label = "BACK", action = "SELECT", fill = 0xAA111827),
            layoutElement(id = "start", type = "button", cx = 0.58f, cy = 0.08f, w = 0.16f, h = 0.05f, label = "START", action = "START", fill = 0xAA111827),
        ),
    )
    return GamepadLayoutConfig(
        id = "standard_gamepad",
        name = "Standard Gamepad",
        layoutKind = "classic_controller",
        portraitCanvas = portrait,
        landscapeCanvas = landscape,
    )
}

private fun buildFpsLayout(): GamepadLayoutConfig {
    val landscape = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "move", type = "joystick", cx = 0.14f, cy = 0.72f, w = 0.24f, h = 0.24f, stick = "left", label = "MOVE", fill = 0x803B82F6, stroke = 0xFF93C5FD),
            layoutElement(id = "look", type = "joystick", cx = 0.78f, cy = 0.70f, w = 0.24f, h = 0.24f, stick = "right", label = "LOOK", fill = 0x80FB7185, stroke = 0xFFFDA4AF),
            layoutElement(id = "shoot", type = "button", cx = 0.88f, cy = 0.36f, w = 0.11f, h = 0.18f, label = "FIRE", action = "mouse_left", fill = 0xCCDC2626),
            layoutElement(id = "aim", type = "button", cx = 0.72f, cy = 0.43f, w = 0.09f, h = 0.16f, label = "AIM", action = "mouse_right", fill = 0xCC2563EB),
            layoutElement(id = "jump", type = "button", cx = 0.61f, cy = 0.28f, w = 0.08f, h = 0.13f, label = "JUMP", action = "keyboard_space", fill = 0xCC10B981),
            layoutElement(id = "crouch", type = "button", cx = 0.62f, cy = 0.48f, w = 0.08f, h = 0.13f, label = "CROUCH", action = "keyboard_ctrl", fill = 0xCC6366F1),
            layoutElement(id = "reload", type = "button", cx = 0.54f, cy = 0.36f, w = 0.1f, h = 0.09f, label = "RELOAD", action = "keyboard_r", fill = 0xCC111827),
            layoutElement(id = "melee", type = "button", cx = 0.46f, cy = 0.39f, w = 0.1f, h = 0.09f, label = "MELEE", action = "keyboard_v", fill = 0xCC111827),
            layoutElement(id = "utility_map", type = "utility", cx = 0.1f, cy = 0.29f, w = 0.07f, h = 0.12f, label = "MAP", action = "keyboard_tab", fill = 0xAA0F172A),
            layoutElement(id = "utility_use", type = "utility", cx = 0.51f, cy = 0.57f, w = 0.1f, h = 0.1f, label = "USE", action = "keyboard_f", fill = 0xCC0F172A),
        ),
    )
    val portrait = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "move", type = "joystick", cx = 0.22f, cy = 0.8f, w = 0.3f, h = 0.18f, stick = "left", label = "MOVE", fill = 0x803B82F6, stroke = 0xFF93C5FD),
            layoutElement(id = "look", type = "joystick", cx = 0.79f, cy = 0.76f, w = 0.3f, h = 0.18f, stick = "right", label = "LOOK", fill = 0x80FB7185, stroke = 0xFFFDA4AF),
            layoutElement(id = "shoot", type = "button", cx = 0.89f, cy = 0.45f, w = 0.14f, h = 0.11f, label = "FIRE", action = "mouse_left", fill = 0xCCDC2626),
            layoutElement(id = "aim", type = "button", cx = 0.72f, cy = 0.52f, w = 0.12f, h = 0.1f, label = "AIM", action = "mouse_right", fill = 0xCC2563EB),
            layoutElement(id = "jump", type = "button", cx = 0.64f, cy = 0.33f, w = 0.1f, h = 0.09f, label = "JUMP", action = "keyboard_space", fill = 0xCC10B981),
            layoutElement(id = "crouch", type = "button", cx = 0.63f, cy = 0.59f, w = 0.1f, h = 0.09f, label = "CROUCH", action = "keyboard_ctrl", fill = 0xCC6366F1),
            layoutElement(id = "reload", type = "button", cx = 0.52f, cy = 0.43f, w = 0.12f, h = 0.07f, label = "RELOAD", action = "keyboard_r", fill = 0xCC111827),
            layoutElement(id = "melee", type = "button", cx = 0.45f, cy = 0.5f, w = 0.12f, h = 0.07f, label = "MELEE", action = "keyboard_v", fill = 0xCC111827),
            layoutElement(id = "utility_map", type = "utility", cx = 0.12f, cy = 0.38f, w = 0.08f, h = 0.08f, label = "MAP", action = "keyboard_tab", fill = 0xAA0F172A),
            layoutElement(id = "utility_use", type = "utility", cx = 0.53f, cy = 0.63f, w = 0.12f, h = 0.08f, label = "USE", action = "keyboard_f", fill = 0xCC0F172A),
        ),
    )
    return GamepadLayoutConfig(
        id = "fps_layout",
        name = "FPS Gaming",
        layoutKind = "touch_mapper",
        gyroEnabled = true,
        portraitCanvas = portrait,
        landscapeCanvas = landscape,
    )
}

private fun buildRacingLayout(): GamepadLayoutConfig {
    val landscape = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "steer", type = "joystick", cx = 0.16f, cy = 0.74f, w = 0.24f, h = 0.24f, stick = "left", label = "STEER", fill = 0x80475569, stroke = 0xFFE2E8F0),
            layoutElement(id = "gas", type = "button", cx = 0.85f, cy = 0.58f, w = 0.13f, h = 0.22f, label = "GAS", action = "keyboard_w", fill = 0xCC16A34A),
            layoutElement(id = "brake", type = "button", cx = 0.7f, cy = 0.58f, w = 0.13f, h = 0.22f, label = "BRAKE", action = "keyboard_s", fill = 0xCCDC2626),
            layoutElement(id = "handbrake", type = "button", cx = 0.78f, cy = 0.84f, w = 0.16f, h = 0.08f, label = "HAND", action = "keyboard_space", fill = 0xCCCA8A04),
            layoutElement(id = "nitro", type = "button", cx = 0.1f, cy = 0.46f, w = 0.11f, h = 0.18f, label = "NITRO", action = "keyboard_shift", fill = 0xCC0891B2),
            layoutElement(id = "gear_up", type = "button", cx = 0.48f, cy = 0.2f, w = 0.1f, h = 0.08f, label = "UP", action = "keyboard_e", fill = 0xCC0F172A),
            layoutElement(id = "gear_down", type = "button", cx = 0.48f, cy = 0.86f, w = 0.1f, h = 0.08f, label = "DOWN", action = "keyboard_q", fill = 0xCC0F172A),
        ),
    )
    val portrait = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "steer", type = "joystick", cx = 0.2f, cy = 0.8f, w = 0.3f, h = 0.18f, stick = "left", label = "STEER", fill = 0x80475569, stroke = 0xFFE2E8F0),
            layoutElement(id = "gas", type = "button", cx = 0.86f, cy = 0.68f, w = 0.16f, h = 0.18f, label = "GAS", action = "keyboard_w", fill = 0xCC16A34A),
            layoutElement(id = "brake", type = "button", cx = 0.69f, cy = 0.68f, w = 0.16f, h = 0.18f, label = "BRAKE", action = "keyboard_s", fill = 0xCCDC2626),
            layoutElement(id = "handbrake", type = "button", cx = 0.78f, cy = 0.88f, w = 0.18f, h = 0.08f, label = "HAND", action = "keyboard_space", fill = 0xCCCA8A04),
            layoutElement(id = "nitro", type = "button", cx = 0.12f, cy = 0.54f, w = 0.11f, h = 0.12f, label = "NITRO", action = "keyboard_shift", fill = 0xCC0891B2),
            layoutElement(id = "gear_up", type = "button", cx = 0.48f, cy = 0.16f, w = 0.14f, h = 0.06f, label = "UP", action = "keyboard_e", fill = 0xCC0F172A),
            layoutElement(id = "gear_down", type = "button", cx = 0.48f, cy = 0.9f, w = 0.14f, h = 0.06f, label = "DOWN", action = "keyboard_q", fill = 0xCC0F172A),
        ),
    )
    return GamepadLayoutConfig(
        id = "racing_layout",
        name = "Racing",
        layoutKind = "classic_controller",
        accelEnabled = true,
        portraitCanvas = portrait,
        landscapeCanvas = landscape,
    )
}

private fun buildShooterHudLayout(): GamepadLayoutConfig {
    val landscape = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "move", type = "joystick", cx = 0.13f, cy = 0.72f, w = 0.24f, h = 0.24f, stick = "left", label = "MOVE", fill = 0x80334155, stroke = 0xFFE5E7EB),
            layoutElement(id = "look", type = "joystick", cx = 0.78f, cy = 0.66f, w = 0.26f, h = 0.26f, stick = "right", label = "AIM", fill = 0x801F2937, stroke = 0xFFF9FAFB),
            layoutElement(id = "fire", type = "button", cx = 0.9f, cy = 0.34f, w = 0.12f, h = 0.18f, label = "FIRE", action = "mouse_left", fill = 0xCCDC2626),
            layoutElement(id = "ads", type = "button", cx = 0.74f, cy = 0.43f, w = 0.09f, h = 0.14f, label = "ADS", action = "mouse_right", fill = 0xCC2563EB),
            layoutElement(id = "jump", type = "button", cx = 0.61f, cy = 0.24f, w = 0.08f, h = 0.13f, label = "JUMP", action = "keyboard_space", fill = 0xCC14B8A6),
            layoutElement(id = "crouch", type = "button", cx = 0.62f, cy = 0.58f, w = 0.08f, h = 0.13f, label = "CROUCH", action = "keyboard_ctrl", fill = 0xCC8B5CF6),
            layoutElement(id = "prone", type = "button", cx = 0.84f, cy = 0.78f, w = 0.09f, h = 0.12f, label = "PRONE", action = "keyboard_z", fill = 0xCC374151),
            layoutElement(id = "reload", type = "button", cx = 0.52f, cy = 0.39f, w = 0.1f, h = 0.08f, label = "RELOAD", action = "keyboard_r", fill = 0xCC111827),
            layoutElement(id = "open", type = "button", cx = 0.52f, cy = 0.51f, w = 0.1f, h = 0.08f, label = "OPEN", action = "keyboard_f", fill = 0xCC111827),
            layoutElement(id = "map", type = "utility", cx = 0.09f, cy = 0.31f, w = 0.07f, h = 0.11f, label = "MAP", action = "keyboard_tab", fill = 0xAA111827),
            layoutElement(id = "inventory", type = "utility", cx = 0.92f, cy = 0.13f, w = 0.06f, h = 0.09f, label = "BAG", action = "keyboard_i", fill = 0xAA111827),
            layoutElement(id = "drive", type = "button", cx = 0.42f, cy = 0.63f, w = 0.1f, h = 0.08f, label = "DRIVE", action = "keyboard_g", fill = 0xCC111827),
        ),
    )
    val portrait = GamepadCanvasConfig(
        elements = listOf(
            layoutElement(id = "move", type = "joystick", cx = 0.2f, cy = 0.82f, w = 0.31f, h = 0.18f, stick = "left", label = "MOVE", fill = 0x80334155, stroke = 0xFFE5E7EB),
            layoutElement(id = "look", type = "joystick", cx = 0.79f, cy = 0.76f, w = 0.34f, h = 0.2f, stick = "right", label = "AIM", fill = 0x801F2937, stroke = 0xFFF9FAFB),
            layoutElement(id = "fire", type = "button", cx = 0.91f, cy = 0.43f, w = 0.14f, h = 0.11f, label = "FIRE", action = "mouse_left", fill = 0xCCDC2626),
            layoutElement(id = "ads", type = "button", cx = 0.74f, cy = 0.51f, w = 0.11f, h = 0.09f, label = "ADS", action = "mouse_right", fill = 0xCC2563EB),
            layoutElement(id = "jump", type = "button", cx = 0.64f, cy = 0.34f, w = 0.1f, h = 0.08f, label = "JUMP", action = "keyboard_space", fill = 0xCC14B8A6),
            layoutElement(id = "crouch", type = "button", cx = 0.64f, cy = 0.63f, w = 0.1f, h = 0.08f, label = "CROUCH", action = "keyboard_ctrl", fill = 0xCC8B5CF6),
            layoutElement(id = "prone", type = "button", cx = 0.86f, cy = 0.86f, w = 0.1f, h = 0.08f, label = "PRONE", action = "keyboard_z", fill = 0xCC374151),
            layoutElement(id = "reload", type = "button", cx = 0.54f, cy = 0.45f, w = 0.12f, h = 0.06f, label = "RELOAD", action = "keyboard_r", fill = 0xCC111827),
            layoutElement(id = "open", type = "button", cx = 0.53f, cy = 0.57f, w = 0.12f, h = 0.06f, label = "OPEN", action = "keyboard_f", fill = 0xCC111827),
            layoutElement(id = "map", type = "utility", cx = 0.12f, cy = 0.39f, w = 0.08f, h = 0.08f, label = "MAP", action = "keyboard_tab", fill = 0xAA111827),
            layoutElement(id = "inventory", type = "utility", cx = 0.9f, cy = 0.15f, w = 0.08f, h = 0.06f, label = "BAG", action = "keyboard_i", fill = 0xAA111827),
            layoutElement(id = "drive", type = "button", cx = 0.42f, cy = 0.69f, w = 0.12f, h = 0.06f, label = "DRIVE", action = "keyboard_g", fill = 0xCC111827),
        ),
    )
    return GamepadLayoutConfig(
        id = "shooter_hud_layout",
        name = "Shooter HUD",
        layoutKind = "touch_mapper",
        gyroEnabled = true,
        portraitCanvas = portrait,
        landscapeCanvas = landscape,
    )
}

private fun layoutElement(
    id: String,
    type: String,
    cx: Float,
    cy: Float,
    w: Float,
    h: Float,
    label: String? = null,
    action: String? = null,
    stick: String? = null,
    trigger: String? = null,
    fill: Long = 0xAA374151,
    stroke: Long = 0xFFFFFFFF,
): LayoutElement {
    return LayoutElement(
        id = id,
        type = type,
        centerX = cx,
        centerY = cy,
        widthRatio = w,
        heightRatio = h,
        label = label,
        action = action,
        stick = stick,
        trigger = trigger,
        colorValue = fill,
        fillColor = fill,
        strokeColor = stroke,
        stylePreset = when (type) {
            "joystick" -> "joystick"
            "trigger" -> "trigger"
            "face_buttons" -> "face_cluster"
            "dpad" -> "dpad"
            "utility" -> "utility"
            else -> "button"
        },
    )
}
