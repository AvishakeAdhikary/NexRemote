package com.neuralnexusstudios.nexremote.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun CameraScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val cameras by appContainer.cameraRepository.cameras.collectAsState()
    val frames by appContainer.cameraRepository.frames.collectAsState()
    val selected = remember { mutableStateListOf<Int>() }
    val active by appContainer.cameraRepository.activeCameras.collectAsState()
    val statusMessage by appContainer.cameraRepository.statusMessage.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()

    val cameraAvailable = sessionState.connected &&
        sessionState.capabilities?.cameraStreaming != false &&
        sessionState.featureStatus["camera"]?.available != false
    val cameraReason = sessionState.featureStatus["camera"]?.reason
        ?: if (sessionState.capabilities?.cameraStreaming == false) "Camera streaming is not supported by the PC server." else null

    LaunchedEffect(cameraAvailable) {
        if (cameraAvailable) {
            appContainer.cameraRepository.requestCameras()
        }
    }

    LaunchedEffect(cameras) {
        if (selected.isEmpty() && cameras.isNotEmpty()) {
            selected += cameras.first().index
        }
    }



    Scaffold(
        topBar = {
            AppTopBar(
                title = "Camera",
                onBack = onBack,
                actions = {
                    IconButton(onClick = { appContainer.cameraRepository.requestCameras() }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Refresh")
                    }
                },
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (cameras.isEmpty()) {
                Text("No cameras found on the PC server.", style = MaterialTheme.typography.bodyLarge)
            } else {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    cameras.forEach { camera ->
                        FilterChip(
                            selected = selected.contains(camera.index),
                            onClick = {
                                if (selected.contains(camera.index)) selected.remove(camera.index) else selected += camera.index
                            },
                            label = { Text(camera.name) },
                        )
                    }
                }
            }

            if (!cameraAvailable) {
                Text(
                    cameraReason ?: "Camera streaming is not ready yet.",
                    color = MaterialTheme.colorScheme.error,
                )
            }

            if (!statusMessage.isNullOrBlank()) {
                Text(
                    text = statusMessage!!,
                    color = if (active.isEmpty()) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Button(
                onClick = {
                    if (active.isEmpty()) appContainer.cameraRepository.start(selected.toSet())
                    else appContainer.cameraRepository.stop()
                },
                enabled = if (active.isEmpty()) selected.isNotEmpty() && cameraAvailable else true,
            ) {
                Text(if (active.isEmpty()) "Start Streaming" else "Stop Streaming")
            }

            if (frames.isEmpty()) {
                Text(
                    if (active.isEmpty()) "Select one or more PC cameras, then start streaming."
                    else "Waiting for live camera frames from the PC host...",
                )
            } else {
                LazyVerticalGrid(columns = GridCells.Adaptive(220.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(frames.entries.toList(), key = { it.key }) { entry ->
                        Card {
                            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(cameras.firstOrNull { it.index == entry.key }?.name ?: "Camera ${entry.key}")
                                val image by rememberJpegImage(entry.value)
                                image?.let { image ->
                                    Image(
                                        bitmap = image,
                                        contentDescription = null,
                                        modifier = Modifier.fillMaxWidth(),
                                        contentScale = ContentScale.Fit,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
