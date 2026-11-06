package com.neuralnexusstudios.nex_remote.ui.screens

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.PhonelinkRing
import androidx.compose.material.icons.outlined.StopCircle
import com.neuralnexusstudios.nex_remote.ui.design.compat.AlertDialog
import com.neuralnexusstudios.nex_remote.ui.design.compat.Button
import com.neuralnexusstudios.nex_remote.ui.design.compat.Card
import com.neuralnexusstudios.nex_remote.ui.design.compat.CardDefaults
import com.neuralnexusstudios.nex_remote.ui.design.compat.Icon
import com.neuralnexusstudios.nex_remote.ui.design.compat.MaterialTheme
import com.neuralnexusstudios.nex_remote.ui.design.compat.OutlinedButton
import com.neuralnexusstudios.nex_remote.ui.design.compat.Scaffold
import com.composables.ui.components.Switch
import com.composables.ui.components.Text
import com.neuralnexusstudios.nex_remote.ui.design.compat.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.core.feature.PhoneScreenRepository.Status
import com.neuralnexusstudios.nex_remote.core.model.ConnectionStatus
import com.neuralnexusstudios.nex_remote.service.NexRemoteControlService
import com.neuralnexusstudios.nex_remote.service.PhoneAudioCapture
import com.neuralnexusstudios.nex_remote.ui.components.AppTopBar

@Composable
fun PhoneScreenShareScreen(appContainer: AppContainer, onBack: () -> Unit) {
    val context = LocalContext.current
    val repository = appContainer.phoneScreenRepository
    val state by repository.state.collectAsState()
    val settings by appContainer.preferences.settings.collectAsState()
    val connection by appContainer.connectionRepository.connectionState.collectAsState()
    val session by appContainer.connectionRepository.serverSessionState.collectAsState()
    val serviceRunning by NexRemoteControlService.running.collectAsState()
    var showDisclosure by rememberSaveable { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    val hostSupports = session.capabilities?.phoneScreen == true
    val hostAllowsControl = session.capabilities?.phoneControl == true

    val captureLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val data = result.data
        if (result.resultCode == Activity.RESULT_OK && data != null) {
            repository.start(result.resultCode, data)
        } else {
            error = "Screen sharing was not started because the capture permission was declined."
        }
    }
    val requestCapture = {
        error = null
        val manager = context.getSystemService(MediaProjectionManager::class.java)
        captureLauncher.launch(manager.createScreenCaptureIntent())
    }
    // The sharing notification (with its Stop button) needs this permission on Android 13+.
    // Sharing still starts if the user declines it.
    val notificationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {
        requestCapture()
    }
    val startSharing = {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            requestCapture()
        }
    }
    val audioPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        repository.setAllowPcAudio(granted)
        if (!granted) error = "Sound sharing needs the audio permission (only sound apps play is shared, never the microphone)."
    }
    val openAccessibilitySettings = {
        context.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    Scaffold(topBar = { AppTopBar(title = "Share my screen", onBack = onBack) }) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            when {
                connection != ConnectionStatus.CONNECTED -> InfoCard("Connect to your PC first, then come back here to share this phone's screen.")
                !hostSupports -> InfoCard(
                    "Your PC is running an older version of NexRemote. Update NexRemote on the PC (Microsoft Store) to show this phone's screen there.",
                )
                else -> {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Outlined.PhonelinkRing, contentDescription = null)
                                Spacer(Modifier.width(12.dp))
                                Text(
                                    text = when (state.status) {
                                        Status.Idle -> "Not sharing"
                                        Status.Starting -> "Starting…"
                                        Status.Sharing -> "Sharing with ${session.serverName.ifBlank { "your PC" }}"
                                    },
                                    style = MaterialTheme.typography.titleMedium,
                                )
                            }
                            Text(
                                "Your screen is sent only to the PC you are connected to, and it is not recorded or stored. " +
                                    "Everything on your screen is visible on the PC while sharing, including notifications.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            if (state.status == Status.Idle) {
                                Button(onClick = startSharing, modifier = Modifier.fillMaxWidth()) { Text("Start sharing") }
                            } else {
                                OutlinedButton(onClick = { repository.stop() }, modifier = Modifier.fillMaxWidth()) {
                                    Icon(Icons.Outlined.StopCircle, contentDescription = null, modifier = Modifier.size(18.dp))
                                    Spacer(Modifier.width(8.dp))
                                    Text("Stop sharing")
                                }
                            }
                            (error ?: state.message)?.let {
                                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }

                    // 1.2: phone audio. Off by default; the PC asks for it per phone.
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            com.neuralnexusstudios.nex_remote.ui.design.NxSwitchRow(
                                title = "Let the PC hear this phone",
                                subtitle = if (PhoneAudioCapture.supported()) {
                                    "While sharing, the PC can play the sound apps on this phone are playing. The microphone is never used."
                                } else {
                                    "Needs Android 10 or newer."
                                },
                                checked = settings.allowPcAudio && PhoneAudioCapture.canCapture(context),
                                enabled = PhoneAudioCapture.supported(),
                                onCheckedChange = { enabled ->
                                    when {
                                        !enabled -> repository.setAllowPcAudio(false)
                                        PhoneAudioCapture.canCapture(context) -> repository.setAllowPcAudio(true)
                                        else -> audioPermission.launch(Manifest.permission.RECORD_AUDIO)
                                    }
                                },
                            )
                            if (session.capabilities?.phoneAudio != true) {
                                Text(
                                    "Update NexRemote on the PC to 1.2 or newer to hear this phone there.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }

                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text("Allow PC control", style = MaterialTheme.typography.titleMedium)
                                    Text(
                                        "Let the PC tap, swipe and press Back, Home and Recents on this phone while you share.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                Switch(
                                    checked = settings.allowPcControl,
                                    onCheckedChange = { enabled ->
                                        when {
                                            !enabled -> repository.setAllowPcControl(false)
                                            !settings.controlDisclosureAccepted -> showDisclosure = true
                                            else -> {
                                                repository.setAllowPcControl(true)
                                                if (!serviceRunning) openAccessibilitySettings()
                                            }
                                        }
                                    },
                                )
                            }
                            if (settings.allowPcControl) {
                                if (serviceRunning) {
                                    Text("PC control is ready.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                                } else {
                                    Text(
                                        "Turn on \"NexRemote PC control\" in Accessibility settings to finish setup.",
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                    TextButton(onClick = openAccessibilitySettings) { Text("Open Accessibility settings") }
                                }
                                if (!hostAllowsControl) {
                                    Text(
                                        "Control is turned off in NexRemote on the PC (Settings › Control shared phone screens).",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showDisclosure) {
        ControlDisclosureDialog(
            onAgree = {
                showDisclosure = false
                appContainer.preferences.setControlDisclosureAccepted()
                repository.setAllowPcControl(true)
                if (!NexRemoteControlService.isRunning) openAccessibilitySettings()
            },
            onDecline = { showDisclosure = false },
        )
    }
}

/** Prominent disclosure shown before the user is sent to enable the AccessibilityService. */
@Composable
private fun ControlDisclosureDialog(onAgree: () -> Unit, onDecline: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDecline,
        title = { Text("Allow your PC to control this phone?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("NexRemote uses Android's Accessibility service for this feature.", fontWeight = FontWeight.SemiBold)
                Text(
                    "What it does: when you share this phone's screen with your paired PC and keep \"Allow PC control\" on, " +
                        "NexRemote performs the taps, swipes and Back, Home and Recents actions you make on the PC.",
                )
                Text(
                    "What it does not do: it does not read what is on your screen, does not see what you type, and does not " +
                        "act when you are not sharing. NexRemote does not collect, store or send any of this data to Neural " +
                        "Nexus Studios or anyone else. Input only comes from the PC you connected to.",
                )
                Text("You can turn this off at any time here or in Android Accessibility settings.")
                Text(
                    "Next, Android opens Accessibility settings. Choose \"NexRemote PC control\" and turn it on.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        },
        confirmButton = { Button(onClick = onAgree) { Text("Agree and continue") } },
        dismissButton = { TextButton(onClick = onDecline) { Text("No thanks") } },
    )
}

@Composable
private fun InfoCard(message: String) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Info, contentDescription = null)
            Spacer(Modifier.width(12.dp))
            Text(message)
        }
    }
}
