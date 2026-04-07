package com.neuralnexusstudios.nexremote.core.storage

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.provider.Settings
import com.neuralnexusstudios.nexremote.core.model.AppSettings
import com.neuralnexusstudios.nexremote.core.model.DefaultGamepadLayouts
import com.neuralnexusstudios.nexremote.core.model.GamepadLayoutConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.util.UUID

class AppPreferences(context: Context) {
    private val appContext = context.applicationContext
    private val prefs: SharedPreferences =
        appContext.getSharedPreferences("nexremote_prefs", Context.MODE_PRIVATE)

    private val json = Json { ignoreUnknownKeys = true }
    private val _settings = MutableStateFlow(loadSettings())

    val settings: StateFlow<AppSettings> = _settings

    fun refresh() {
        _settings.value = loadSettings()
    }

    fun recordTermsAccepted() {
        prefs.edit()
            .putBoolean(KEY_TERMS_ACCEPTED, true)
            .putString(KEY_TERMS_ACCEPTED_AT, java.time.Instant.now().toString())
            .apply()
        refresh()
    }

    fun setCameraDisclosureAccepted() {
        prefs.edit().putBoolean(KEY_CAMERA_DISCLOSURE, true).apply()
        refresh()
    }

    fun updateDeviceName(value: String) {
        prefs.edit().putString(KEY_DEVICE_NAME, value.ifBlank { resolveInitialDeviceName() }).apply()
        refresh()
    }

    fun updateAutoConnect(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_AUTO_CONNECT, enabled).apply()
        refresh()
    }

    fun updateGyroSensitivity(value: Float) {
        prefs.edit().putFloat(KEY_GYRO_SENSITIVITY, value).apply()
        refresh()
    }

    fun updateAppHaptics(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_APP_HAPTICS, enabled).apply()
        refresh()
    }

    fun updateUseSecureConnection(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_USE_SECURE_CONNECTION, enabled).apply()
        refresh()
    }

    fun updateLastServer(value: String?) {
        prefs.edit().putString(KEY_LAST_SERVER, value).apply()
        refresh()
    }

    fun loadLayouts(): Pair<List<GamepadLayoutConfig>, String> {
        val encoded = prefs.getString(KEY_LAYOUTS_JSON, null)
        val activeLayoutId = prefs.getString(KEY_ACTIVE_LAYOUT_ID, DefaultGamepadLayouts.builtIns.first().id)
            ?: DefaultGamepadLayouts.builtIns.first().id
        val customLayouts = encoded?.let {
            runCatching { json.decodeFromString<List<GamepadLayoutConfig>>(it) }.getOrDefault(emptyList())
        }.orEmpty()
        val merged = DefaultGamepadLayouts.builtIns.filterNot { builtIn ->
            customLayouts.any { it.id == builtIn.id }
        } + customLayouts
        return merged to activeLayoutId
    }

    fun saveLayouts(layouts: List<GamepadLayoutConfig>, activeLayoutId: String) {
        val customLayouts = layouts.filterNot { layout ->
            DefaultGamepadLayouts.builtIns.any { it.id == layout.id }
        }
        prefs.edit()
            .putString(KEY_LAYOUTS_JSON, json.encodeToString(customLayouts))
            .putString(KEY_ACTIVE_LAYOUT_ID, activeLayoutId)
            .apply()
    }

    private fun loadSettings(): AppSettings {
        val deviceId = prefs.getString(KEY_DEVICE_ID, null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString(KEY_DEVICE_ID, it).apply()
        }
        val resolvedDefaultDeviceName = resolveInitialDeviceName()
        val storedDeviceName = prefs.getString(KEY_DEVICE_NAME, null)
        val deviceName = when {
            storedDeviceName.isNullOrBlank() || storedDeviceName == LEGACY_DEFAULT_DEVICE_NAME -> {
                prefs.edit().putString(KEY_DEVICE_NAME, resolvedDefaultDeviceName).apply()
                resolvedDefaultDeviceName
            }
            else -> storedDeviceName
        }
        return AppSettings(
            deviceId = deviceId,
            deviceName = deviceName,
            lastServer = prefs.getString(KEY_LAST_SERVER, null),
            autoConnect = prefs.getBoolean(KEY_AUTO_CONNECT, false),
            gyroSensitivity = prefs.getFloat(KEY_GYRO_SENSITIVITY, 1f),
            appHapticsEnabled = prefs.getBoolean(KEY_APP_HAPTICS, true),
            useSecureConnection = prefs.getBoolean(KEY_USE_SECURE_CONNECTION, true),
            termsAccepted = prefs.getBoolean(KEY_TERMS_ACCEPTED, false),
            termsAcceptedAt = prefs.getString(KEY_TERMS_ACCEPTED_AT, null),
            cameraDisclosureAccepted = prefs.getBoolean(KEY_CAMERA_DISCLOSURE, false),
        )
    }

    private fun resolveInitialDeviceName(): String {
        val configuredName = runCatching {
            Settings.Global.getString(appContext.contentResolver, "device_name")
        }.getOrNull()?.trim().orEmpty()
        if (configuredName.isNotBlank()) {
            return configuredName
        }

        val model = Build.MODEL?.trim().orEmpty()
        val manufacturer = Build.MANUFACTURER?.trim().orEmpty()
        val combined = when {
            model.isBlank() && manufacturer.isBlank() -> ""
            manufacturer.isBlank() -> model
            model.isBlank() -> manufacturer
            model.startsWith(manufacturer, ignoreCase = true) -> model
            else -> "$manufacturer $model"
        }
        if (combined.isNotBlank()) {
            return combined
        }

        val device = Build.DEVICE?.trim().orEmpty()
        if (device.isNotBlank()) {
            return device
        }

        return LEGACY_DEFAULT_DEVICE_NAME
    }

    companion object {
        private const val LEGACY_DEFAULT_DEVICE_NAME = "Android Device"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_DEVICE_NAME = "device_name"
        private const val KEY_LAST_SERVER = "last_server"
        private const val KEY_AUTO_CONNECT = "auto_connect"
        private const val KEY_GYRO_SENSITIVITY = "gyro_sensitivity"
        private const val KEY_APP_HAPTICS = "app_haptics"
        private const val KEY_USE_SECURE_CONNECTION = "use_secure_connection"
        private const val KEY_TERMS_ACCEPTED = "terms_accepted"
        private const val KEY_TERMS_ACCEPTED_AT = "terms_accepted_at"
        private const val KEY_LAYOUTS_JSON = "gamepad_layouts_json"
        private const val KEY_ACTIVE_LAYOUT_ID = "gamepad_active_layout_id"
        private const val KEY_CAMERA_DISCLOSURE = "camera_disclosure_accepted"
    }
}
