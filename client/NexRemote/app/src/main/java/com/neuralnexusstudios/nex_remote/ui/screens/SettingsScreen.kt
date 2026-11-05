package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Autorenew
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Vibration
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.composables.ui.components.HorizontalSeparator
import com.composables.ui.components.Slider
import com.composables.ui.components.Text
import com.neuralnexusstudios.nex_remote.BuildConfig
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.core.model.ThemeMode
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxCard
import com.neuralnexusstudios.nex_remote.ui.design.NxScaffold
import com.neuralnexusstudios.nex_remote.ui.design.NxSectionLabel
import com.neuralnexusstudios.nex_remote.ui.design.NxSegmented
import com.neuralnexusstudios.nex_remote.ui.design.NxSwitchRow
import com.neuralnexusstudios.nex_remote.ui.design.NxTextField
import com.neuralnexusstudios.nex_remote.ui.design.NxType

@Composable
fun SettingsScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val settings by appContainer.preferences.settings.collectAsState()
    var deviceName by remember(settings.deviceName) { mutableStateOf(settings.deviceName) }

    NxScaffold(title = "Settings", onBack = onBack) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            NxSectionLabel("This phone")
            NxCard(Modifier.fillMaxWidth()) {
                NxTextField(
                    value = deviceName,
                    onValueChange = {
                        deviceName = it
                        appContainer.preferences.updateDeviceName(it)
                    },
                    label = "Device name shown on your PC",
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            NxSectionLabel("Appearance")
            NxCard(Modifier.fillMaxWidth()) {
                Text("Theme", style = NxType.titleSmall)
                val modes = listOf(ThemeMode.Dark, ThemeMode.Light, ThemeMode.System)
                NxSegmented(
                    options = listOf("Dark", "Light", "System"),
                    selectedIndex = modes.indexOf(settings.themeMode).coerceAtLeast(0),
                    onSelect = { appContainer.preferences.updateThemeMode(modes[it]) },
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            NxSectionLabel("Connection & feedback")
            NxCard(Modifier.fillMaxWidth(), contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 14.dp, vertical = 6.dp)) {
                NxSwitchRow(
                    title = "Auto-connect",
                    subtitle = "Reconnect to the last PC when possible.",
                    icon = Icons.Outlined.Autorenew,
                    checked = settings.autoConnect,
                    onCheckedChange = appContainer.preferences::updateAutoConnect,
                )
                HorizontalSeparator()
                NxSwitchRow(
                    title = "Prefer secure connection",
                    subtitle = "Try the encrypted port first, then fall back to the local-network port.",
                    icon = Icons.Outlined.Lock,
                    checked = settings.useSecureConnection,
                    onCheckedChange = appContainer.preferences::updateUseSecureConnection,
                )
                HorizontalSeparator()
                NxSwitchRow(
                    title = "Haptics",
                    subtitle = "Vibration feedback on buttons and controls.",
                    icon = Icons.Outlined.Vibration,
                    checked = settings.appHapticsEnabled,
                    onCheckedChange = appContainer.preferences::updateAppHaptics,
                )
            }

            NxSectionLabel("Motion controls")
            NxCard(Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text("Gyroscope sensitivity", style = NxType.titleSmall, modifier = Modifier.weight(1f))
                    Text("${"%.1f".format(settings.gyroSensitivity)}x", style = NxType.label, color = Nx.primary)
                }
                Slider(
                    value = settings.gyroSensitivity,
                    onValueChange = appContainer.preferences::updateGyroSensitivity,
                    valueRange = 0.1f..5f,
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            Text(
                "NexRemote ${BuildConfig.VERSION_NAME} · Neural Nexus Studios",
                style = NxType.bodySmall,
                color = Nx.muted,
                modifier = Modifier.padding(start = 4.dp, top = 8.dp, bottom = 24.dp),
            )
        }
    }
}
