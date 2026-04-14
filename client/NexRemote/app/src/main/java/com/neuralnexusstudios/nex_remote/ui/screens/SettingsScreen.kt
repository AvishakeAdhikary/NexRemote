package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.ui.components.AppTopBar

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val settings by appContainer.preferences.settings.collectAsState()
    var deviceName by remember(settings.deviceName) { mutableStateOf(settings.deviceName) }

    Scaffold(
        topBar = {
            AppTopBar(title = "Settings", onBack = onBack)
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            OutlinedTextField(
                value = deviceName,
                onValueChange = {
                    deviceName = it
                    appContainer.preferences.updateDeviceName(it)
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Device Name") },
            )

            SettingSwitchRow(
                title = "Auto-connect",
                subtitle = "Reconnect to the last discovered or manually entered PC when possible.",
                checked = settings.autoConnect,
                onCheckedChange = appContainer.preferences::updateAutoConnect,
            )

            SettingSwitchRow(
                title = "App haptics",
                subtitle = "Enable vibration and haptic feedback for supported buttons and controls across the app.",
                checked = settings.appHapticsEnabled,
                onCheckedChange = appContainer.preferences::updateAppHaptics,
            )

            SettingSwitchRow(
                title = "Prefer secure connection",
                subtitle = "Try the secure WebSocket port before falling back to insecure local network transport.",
                checked = settings.useSecureConnection,
                onCheckedChange = appContainer.preferences::updateUseSecureConnection,
            )

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Gyroscope Sensitivity", style = MaterialTheme.typography.titleMedium)
                Slider(
                    value = settings.gyroSensitivity,
                    onValueChange = appContainer.preferences::updateGyroSensitivity,
                    valueRange = 0.1f..5f,
                )
                Text("Current: ${"%.1f".format(settings.gyroSensitivity)}x")
            }

            Text(
                "NexRemote 1.0.0\nDeveloped by Neural Nexus Studios",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun SettingSwitchRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, style = MaterialTheme.typography.bodySmall)
        }
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}
