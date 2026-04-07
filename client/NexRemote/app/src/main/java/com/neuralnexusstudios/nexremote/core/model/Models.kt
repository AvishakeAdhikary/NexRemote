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
data class LayoutElement(
    val id: String,
    val type: String,
    val x: Float,
    val y: Float,
    val width: Float,
    val height: Float,
    val scale: Float = 1f,
    val colorValue: Long = 0xFF374151,
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
    val orientation: String = "landscape",
    val gyroEnabled: Boolean = false,
    val accelEnabled: Boolean = false,
    val hapticFeedback: Boolean = true,
    val mode: String = "xinput",
    val elements: List<LayoutElement>,
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
        GamepadLayoutConfig(
            id = "standard_gamepad",
            name = "Standard Gamepad",
            elements = listOf(
                LayoutElement("dpad", "dpad", 0.04f, 0.32f, 120f, 120f),
                LayoutElement("left_stick", "joystick", 0.20f, 0.55f, 100f, 100f, stick = "left"),
                LayoutElement("right_stick", "joystick", 0.62f, 0.55f, 100f, 100f, stick = "right"),
                LayoutElement("face_buttons", "face_buttons", 0.76f, 0.32f, 120f, 120f),
                LayoutElement("l1", "button", 0.04f, 0.05f, 70f, 36f, label = "L1", action = "L1"),
                LayoutElement("l2", "trigger", 0.04f, 0.18f, 70f, 36f, label = "L2", trigger = "LT"),
                LayoutElement("r1", "button", 0.83f, 0.05f, 70f, 36f, label = "R1", action = "R1"),
                LayoutElement("r2", "trigger", 0.83f, 0.18f, 70f, 36f, label = "R2", trigger = "RT"),
                LayoutElement("select", "button", 0.37f, 0.75f, 76f, 32f, label = "SELECT", action = "SELECT"),
                LayoutElement("start", "button", 0.52f, 0.75f, 76f, 32f, label = "START", action = "START"),
            ),
        ),
        GamepadLayoutConfig(
            id = "fps_layout",
            name = "FPS Gaming",
            gyroEnabled = true,
            elements = listOf(
                LayoutElement("left_stick", "joystick", 0.06f, 0.52f, 110f, 110f, stick = "left"),
                LayoutElement("shoot", "button", 0.78f, 0.40f, 90f, 90f, label = "FIRE", action = "mouse_left", colorValue = 0xFFFF0000),
                LayoutElement("aim", "button", 0.65f, 0.45f, 70f, 70f, label = "AIM", action = "mouse_right", colorValue = 0xFF2E7D32),
                LayoutElement("jump", "button", 0.23f, 0.35f, 68f, 68f, label = "JUMP", action = "keyboard_space", colorValue = 0xFF1565C0),
                LayoutElement("crouch", "button", 0.06f, 0.35f, 68f, 68f, label = "DUCK", action = "keyboard_ctrl", colorValue = 0xFF1565C0),
                LayoutElement("reload", "button", 0.78f, 0.70f, 68f, 42f, label = "RELOAD", action = "keyboard_r"),
                LayoutElement("melee", "button", 0.65f, 0.70f, 68f, 42f, label = "MELEE", action = "keyboard_v"),
            ),
        ),
        GamepadLayoutConfig(
            id = "racing_layout",
            name = "Racing",
            accelEnabled = true,
            elements = listOf(
                LayoutElement("gas", "button", 0.84f, 0.38f, 90f, 100f, label = "GAS", action = "keyboard_w", colorValue = 0xFF2E7D32),
                LayoutElement("brake", "button", 0.72f, 0.38f, 90f, 100f, label = "BRAKE", action = "keyboard_s", colorValue = 0xFFFF0000),
                LayoutElement("handbrake", "button", 0.84f, 0.72f, 90f, 48f, label = "HAND", action = "keyboard_space", colorValue = 0xFFFFC107),
                LayoutElement("nitro", "button", 0.04f, 0.45f, 90f, 90f, label = "NITRO", action = "keyboard_shift", colorValue = 0xFF00BCD4),
                LayoutElement("gear_up", "button", 0.44f, 0.05f, 70f, 40f, label = "UP", action = "keyboard_e"),
                LayoutElement("gear_down", "button", 0.44f, 0.75f, 70f, 40f, label = "DOWN", action = "keyboard_q"),
            ),
        ),
    )
}
