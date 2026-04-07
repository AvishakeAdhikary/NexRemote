package com.neuralnexusstudios.nexremote.ui.screens

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Fullscreen
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.TouchApp
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.core.model.DisplayInfo
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun ScreenShareScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val displays by appContainer.screenShareRepository.displays.collectAsState()
    val frames by appContainer.screenShareRepository.frames.collectAsState()
    val active by appContainer.screenShareRepository.activeDisplays.collectAsState()
    val audioEnabled by appContainer.screenShareRepository.audioEnabled.collectAsState()
    val audioStatusMessage by appContainer.screenShareRepository.audioStatusMessage.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    var fps by remember { mutableIntStateOf(30) }
    var quality by remember { mutableStateOf("medium") }
    var resolution by remember { mutableStateOf("native") }
    var interactive by remember { mutableStateOf(false) }
    var fullScreenDisplay by remember { mutableStateOf<Int?>(null) }
    val selected = remember { mutableStateListOf<Int>() }

    val screenShareAvailable = sessionState.connected &&
        sessionState.capabilities?.screenStreaming != false &&
        sessionState.featureStatus["screen_share"]?.available != false
    val screenShareReason = sessionState.featureStatus["screen_share"]?.reason
        ?: if (sessionState.capabilities?.screenStreaming == false) "Screen share is not supported by the PC server." else null
    val screenAudioAvailable = sessionState.connected &&
        sessionState.capabilities?.screenAudioStreaming != false &&
        sessionState.featureStatus["screen_audio"]?.available != false
    val screenAudioReason = sessionState.featureStatus["screen_audio"]?.reason
        ?: if (sessionState.capabilities?.screenAudioStreaming == false) "PC audio streaming is not supported by the server." else null

    LaunchedEffect(screenShareAvailable) {
        if (screenShareAvailable) {
            appContainer.screenShareRepository.requestDisplays()
        }
    }

    LaunchedEffect(displays) {
        if (selected.isEmpty() && displays.isNotEmpty()) {
            selected += displays.first().index
        }
    }



    if (fullScreenDisplay != null) {
        FullScreenSharePage(
            display = displays.firstOrNull { it.index == fullScreenDisplay } ?: DisplayInfo(fullScreenDisplay!!, "Display", 1920, 1080),
            frame = frames[fullScreenDisplay],
            interactive = interactive,
            onBack = { fullScreenDisplay = null },
            onToggleInteractive = { interactive = !interactive },
            onStop = {
                appContainer.screenShareRepository.stop()
                fullScreenDisplay = null
            },
            onSendInput = { action, x, y, extras ->
                appContainer.screenShareRepository.sendInput(fullScreenDisplay!!, action, x, y, extras)
            },
        )
        return
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = "Screen Share",
                onBack = onBack,
                actions = {
                    IconButton(onClick = { appContainer.screenShareRepository.requestDisplays() }) {
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
            if (displays.isNotEmpty()) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    displays.forEach { display ->
                        FilterChip(
                            selected = selected.contains(display.index),
                            onClick = {
                                if (selected.contains(display.index)) selected.remove(display.index) else selected += display.index
                            },
                            label = { Text("${display.name} ${display.width}x${display.height}") },
                        )
                    }
                }
            }

            Text("Resolution", style = MaterialTheme.typography.titleMedium)
            SingleChoiceSegmentedButtonRow {
                listOf("native", "1080p", "720p", "480p").forEachIndexed { index, label ->
                    SegmentedButton(
                        selected = resolution == label,
                        onClick = {
                            resolution = label
                            appContainer.screenShareRepository.setResolution(label)
                        },
                        shape = androidx.compose.material3.SegmentedButtonDefaults.itemShape(index, 4),
                    ) { Text(label) }
                }
            }

            Text("Quality", style = MaterialTheme.typography.titleMedium)
            SingleChoiceSegmentedButtonRow {
                listOf("low", "medium", "high", "ultra").forEachIndexed { index, label ->
                    SegmentedButton(
                        selected = quality == label,
                        onClick = {
                            quality = label
                            appContainer.screenShareRepository.setQuality(
                                when (label) {
                                    "low" -> 30
                                    "medium" -> 50
                                    "high" -> 70
                                    else -> 90
                                },
                            )
                        },
                        shape = androidx.compose.material3.SegmentedButtonDefaults.itemShape(index, 4),
                    ) { Text(label) }
                }
            }

            Text("FPS: $fps")
            Slider(
                value = fps.toFloat(),
                onValueChange = { fps = it.toInt() },
                onValueChangeFinished = { appContainer.screenShareRepository.setFps(fps) },
                valueRange = 5f..60f,
            )

            if (!screenShareAvailable) {
                Text(
                    screenShareReason ?: "Screen share is not ready yet.",
                    color = MaterialTheme.colorScheme.error,
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = {
                        if (active.isEmpty()) appContainer.screenShareRepository.start(selected.toList(), fps, quality, resolution, audioEnabled && screenAudioAvailable)
                        else appContainer.screenShareRepository.stop()
                    },
                    enabled = if (active.isEmpty()) selected.isNotEmpty() && screenShareAvailable else true,
                ) {
                    Text(if (active.isEmpty()) "Start Streaming" else "Stop Streaming")
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Interactive")
                    Switch(checked = interactive, onCheckedChange = { interactive = it })
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Text("System audio")
                Switch(
                    checked = audioEnabled,
                    onCheckedChange = { enabled ->
                        appContainer.screenShareRepository.setAudioEnabled(enabled)
                    },
                    enabled = screenAudioAvailable || audioEnabled,
                )
            }

            if (!screenAudioAvailable && !screenAudioReason.isNullOrBlank()) {
                Text(
                    screenAudioReason,
                    color = MaterialTheme.colorScheme.error,
                )
            }

            if (!audioStatusMessage.isNullOrBlank()) {
                Text(
                    audioStatusMessage!!,
                    color = if (audioEnabled) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.error,
                )
            }

            if (frames.isEmpty()) {
                Text("Select one or more displays and start streaming.")
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(240.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(frames.entries.toList(), key = { it.key }) { entry ->
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                                    Text(displays.firstOrNull { it.index == entry.key }?.name ?: "Display ${entry.key + 1}")
                                    IconButton(onClick = { fullScreenDisplay = entry.key }) {
                                        Icon(Icons.Outlined.Fullscreen, contentDescription = "Fullscreen")
                                    }
                                }
                                ScreenFrame(
                                    frame = entry.value,
                                    interactive = interactive,
                                    onOpenFullScreen = { fullScreenDisplay = entry.key },
                                    onSendInput = { action, x, y, extras ->
                                        appContainer.screenShareRepository.sendInput(entry.key, action, x, y, extras)
                                    },
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FullScreenSharePage(
    display: DisplayInfo,
    frame: ByteArray?,
    interactive: Boolean,
    onBack: () -> Unit,
    onToggleInteractive: () -> Unit,
    onStop: () -> Unit,
    onSendInput: (String, Float, Float, Map<String, Any?>) -> Unit,
) {
    Scaffold(
        topBar = {
            AppTopBar(
                title = display.name,
                onBack = onBack,
                actions = {
                    IconButton(onClick = onToggleInteractive) {
                        Icon(Icons.Outlined.TouchApp, contentDescription = "Toggle interactive")
                    }
                    TextButton(onClick = onStop) {
                        Text("Stop")
                    }
                },
            )
        },
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(12.dp),
        ) {
            if (frame == null) {
                Text("Waiting for the next frame...", modifier = Modifier.align(androidx.compose.ui.Alignment.Center))
            } else {
                ScreenFrame(
                    frame = frame,
                    interactive = interactive,
                    onOpenFullScreen = {},
                    onSendInput = onSendInput,
                    modifier = Modifier.fillMaxSize(),
                    fullScreen = true,
                    transformStateKey = display.index,
                )
            }
        }
    }
}

@Composable
private fun ScreenFrame(
    frame: ByteArray,
    interactive: Boolean,
    onOpenFullScreen: () -> Unit,
    onSendInput: (String, Float, Float, Map<String, Any?>) -> Unit,
    modifier: Modifier = Modifier.fillMaxWidth(),
    fullScreen: Boolean = false,
    transformStateKey: Any? = null,
) {
    var lastX by remember { mutableStateOf(0.5f) }
    var lastY by remember { mutableStateOf(0.5f) }
    var zoomScale by remember(transformStateKey, fullScreen) { mutableStateOf(1f) }
    var zoomOffset by remember(transformStateKey, fullScreen) { mutableStateOf(Offset.Zero) }

    LaunchedEffect(fullScreen, interactive, transformStateKey) {
        if (!fullScreen || interactive) {
            zoomScale = 1f
            zoomOffset = Offset.Zero
        }
    }

    val image by rememberJpegImage(frame)
    image?.let { image ->
        val aspectRatio = image.width.toFloat() / image.height.toFloat().coerceAtLeast(1f)
        val transformEnabled = fullScreen && !interactive
        val contentModifier = if (fullScreen) {
            modifier
        } else {
            modifier
                .fillMaxWidth()
                .aspectRatio(aspectRatio)
        }
        Box(
            modifier = contentModifier
                .pointerInput(transformStateKey, transformEnabled) {
                    if (transformEnabled) {
                        detectTransformGestures { _, pan, zoom, _ ->
                            val newScale = (zoomScale * zoom).coerceIn(1f, 4f)
                            val nextOffset = if (newScale <= 1f) {
                                Offset.Zero
                            } else {
                                val maxX = ((size.width * newScale) - size.width) / 2f
                                val maxY = ((size.height * newScale) - size.height) / 2f
                                Offset(
                                    x = (zoomOffset.x + pan.x).coerceIn(-maxX, maxX),
                                    y = (zoomOffset.y + pan.y).coerceIn(-maxY, maxY),
                                )
                            }
                            zoomScale = newScale
                            zoomOffset = nextOffset
                        }
                    }
                }
                .pointerInput(interactive) {
                    if (interactive) {
                        detectTapGestures(
                            onTap = { offset ->
                                mapPointerToNormalized(offset, size.width.toFloat(), size.height.toFloat(), image.width, image.height)?.let { (x, y) ->
                                    lastX = x
                                    lastY = y
                                    onSendInput("click", x, y, mapOf("button" to "left", "count" to 1))
                                }
                            },
                            onDoubleTap = { offset ->
                                mapPointerToNormalized(offset, size.width.toFloat(), size.height.toFloat(), image.width, image.height)?.let { (x, y) ->
                                    lastX = x
                                    lastY = y
                                    onSendInput("click", x, y, mapOf("button" to "left", "count" to 2))
                                }
                            },
                            onLongPress = { offset ->
                                mapPointerToNormalized(offset, size.width.toFloat(), size.height.toFloat(), image.width, image.height)?.let { (x, y) ->
                                    lastX = x
                                    lastY = y
                                    onSendInput("click", x, y, mapOf("button" to "right", "count" to 1))
                                }
                            },
                        )
                    } else {
                        detectTapGestures(onTap = { onOpenFullScreen() })
                    }
                }
                .pointerInput(interactive) {
                    if (interactive) {
                        detectDragGestures(
                            onDragStart = { offset ->
                                mapPointerToNormalized(offset, size.width.toFloat(), size.height.toFloat(), image.width, image.height)?.let { (x, y) ->
                                    lastX = x
                                    lastY = y
                                    onSendInput("press", x, y, mapOf("button" to "left"))
                                }
                            },
                            onDrag = { change, _ ->
                                mapPointerToNormalized(change.position, size.width.toFloat(), size.height.toFloat(), image.width, image.height)?.let { (x, y) ->
                                    lastX = x
                                    lastY = y
                                    onSendInput("move", x, y, emptyMap())
                                }
                            },
                            onDragEnd = {
                                onSendInput("release", lastX, lastY, mapOf("button" to "left"))
                            },
                        )
                    }
                },
        ) {
            Image(
                bitmap = image,
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .fillMaxSize()
                    .graphicsLayer {
                        scaleX = zoomScale
                        scaleY = zoomScale
                        translationX = zoomOffset.x
                        translationY = zoomOffset.y
                    },
            )
        }
    }
}

private fun mapPointerToNormalized(
    offset: Offset,
    containerWidth: Float,
    containerHeight: Float,
    imageWidth: Int,
    imageHeight: Int,
): Pair<Float, Float>? {
    if (containerWidth <= 0f || containerHeight <= 0f || imageWidth <= 0 || imageHeight <= 0) {
        return null
    }

    val scale = minOf(containerWidth / imageWidth, containerHeight / imageHeight)
    val fittedWidth = imageWidth * scale
    val fittedHeight = imageHeight * scale
    val left = (containerWidth - fittedWidth) / 2f
    val top = (containerHeight - fittedHeight) / 2f
    if (offset.x !in left..(left + fittedWidth) || offset.y !in top..(top + fittedHeight)) {
        return null
    }

    val x = ((offset.x - left) / fittedWidth).coerceIn(0f, 1f)
    val y = ((offset.y - top) / fittedHeight).coerceIn(0f, 1f)
    return x to y
}
