package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.VolumeDown
import androidx.compose.material.icons.automirrored.outlined.VolumeMute
import androidx.compose.material.icons.automirrored.outlined.VolumeUp
import androidx.compose.material.icons.outlined.FastForward
import androidx.compose.material.icons.outlined.FastRewind
import androidx.compose.material.icons.outlined.MusicNote
import androidx.compose.material.icons.outlined.Pause
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Stop
import com.neuralnexusstudios.nex_remote.ui.design.compat.Button
import com.neuralnexusstudios.nex_remote.ui.design.compat.Card
import com.neuralnexusstudios.nex_remote.ui.design.compat.Icon
import com.neuralnexusstudios.nex_remote.ui.design.compat.MaterialTheme
import com.neuralnexusstudios.nex_remote.ui.design.compat.Scaffold
import com.composables.ui.components.Slider
import com.composables.ui.components.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.ui.components.AppTopBar

@Composable
fun MediaControlScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val state by appContainer.mediaRepository.state.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    val mediaAvailable = sessionState.connected && sessionState.featureStatus["media_control"]?.available != false
    val mediaReason = sessionState.featureStatus["media_control"]?.reason
    var pendingVolume by remember { mutableFloatStateOf(state.volume.toFloat().coerceAtLeast(0f)) }

    LaunchedEffect(mediaAvailable) {
        if (mediaAvailable) {
            appContainer.mediaRepository.requestInfo()
        }
    }

    LaunchedEffect(state.volume) {
        pendingVolume = state.volume.toFloat().coerceIn(0f, 100f)
    }

    Scaffold(
        topBar = {
            AppTopBar(title = "Media Control", onBack = onBack)
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            if (!mediaAvailable) {
                Card {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Media control is not ready", style = MaterialTheme.typography.titleMedium)
                        Text(mediaReason ?: "The PC server has not enabled media control yet.", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            Card {
                Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Outlined.MusicNote, contentDescription = null)
                    Text(state.title, style = MaterialTheme.typography.headlineSmall)
                    Text(state.artist.ifBlank { "No artist information" }, style = MaterialTheme.typography.bodyMedium)
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                MediaButton("Prev", Icons.Outlined.FastRewind, modifier = Modifier.weight(1f), enabled = mediaAvailable) { appContainer.mediaRepository.previous() }
                MediaButton(if (state.isPlaying) "Pause" else "Play", if (state.isPlaying) Icons.Outlined.Pause else Icons.Outlined.PlayArrow, modifier = Modifier.weight(1f), enabled = mediaAvailable) {
                    if (state.isPlaying) appContainer.mediaRepository.pause() else appContainer.mediaRepository.play()
                }
                MediaButton("Stop", Icons.Outlined.Stop, modifier = Modifier.weight(1f), enabled = mediaAvailable) { appContainer.mediaRepository.stop() }
                MediaButton("Next", Icons.Outlined.FastForward, modifier = Modifier.weight(1f), enabled = mediaAvailable) { appContainer.mediaRepository.next() }
            }

            Card {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Volume", style = MaterialTheme.typography.titleMedium)
                    Slider(
                        value = pendingVolume.coerceIn(0f, 100f),
                        onValueChange = { pendingVolume = it },
                        onValueChangeFinished = { if (mediaAvailable) appContainer.mediaRepository.setVolume(pendingVolume.toInt()) },
                        valueRange = 0f..100f,
                        enabled = mediaAvailable,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                        MediaButton("Mute", Icons.AutoMirrored.Outlined.VolumeMute, modifier = Modifier.weight(1f), enabled = mediaAvailable) { appContainer.mediaRepository.muteToggle() }
                        MediaButton("Vol -", Icons.AutoMirrored.Outlined.VolumeDown, modifier = Modifier.weight(1f), enabled = mediaAvailable) { appContainer.mediaRepository.volumeDown() }
                        MediaButton("Vol +", Icons.AutoMirrored.Outlined.VolumeUp, modifier = Modifier.weight(1f), enabled = mediaAvailable) { appContainer.mediaRepository.volumeUp() }
                    }
                }
            }
        }
    }
}

@Composable
private fun MediaButton(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    // Round transport button: icon with a small caption underneath.
    androidx.compose.foundation.layout.Column(
        modifier = modifier,
        horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        com.neuralnexusstudios.nex_remote.ui.design.NxIconButton(
            icon = icon,
            contentDescription = label,
            onClick = onClick,
            enabled = enabled,
            filled = true,
            modifier = Modifier.size(60.dp),
        )
        Text(label, style = com.neuralnexusstudios.nex_remote.ui.design.NxType.label, color = com.neuralnexusstudios.nex_remote.ui.design.Nx.muted)
    }
}
