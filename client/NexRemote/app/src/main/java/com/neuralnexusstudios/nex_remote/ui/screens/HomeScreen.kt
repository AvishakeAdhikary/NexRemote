package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ScreenShare
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.Folder
import androidx.compose.material.icons.outlined.Gamepad
import androidx.compose.material.icons.outlined.MusicNote
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.TaskAlt
import androidx.compose.material.icons.outlined.TouchApp
import androidx.compose.material.icons.outlined.Usb
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.core.model.ConnectionStatus
import com.neuralnexusstudios.nex_remote.core.model.ServerSessionState
import com.neuralnexusstudios.nex_remote.ui.components.AppTopBar
import kotlinx.coroutines.launch

@OptIn(ExperimentalLayoutApi::class, ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    appContainer: AppContainer,
    onOpenConnection: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenGamepad: () -> Unit,
    onOpenTouchpad: () -> Unit,
    onOpenMedia: () -> Unit,
    onOpenCamera: () -> Unit,
    onOpenScreenShare: () -> Unit,
    onOpenFileExplorer: () -> Unit,
    onOpenTaskManager: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val snackbars = remember { SnackbarHostState() }
    val connectionState by appContainer.connectionRepository.connectionState.collectAsState()
    val deviceName by appContainer.connectionRepository.connectedDeviceName.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()

    val features = listOf(
        FeatureItem("Gamepad", "gamepad", Icons.Outlined.Gamepad, onOpenGamepad),
        FeatureItem("Touchpad", "touchpad", Icons.Outlined.TouchApp, onOpenTouchpad),
        FeatureItem("Media Control", "media_control", Icons.Outlined.MusicNote, onOpenMedia),
        FeatureItem("Camera", "camera", Icons.Outlined.CameraAlt, onOpenCamera),
        FeatureItem("Screen Share", "screen_share", Icons.AutoMirrored.Outlined.ScreenShare, onOpenScreenShare),
        FeatureItem("File Explorer", "file_explorer", Icons.Outlined.Folder, onOpenFileExplorer),
        FeatureItem("Task Manager", "task_manager", Icons.Outlined.TaskAlt, onOpenTaskManager),
    ).map { feature ->
        val availability = resolveFeatureAvailability(sessionState, feature.key, feature.title)
        feature.copy(enabled = availability.first, statusText = availability.second)
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = "NexRemote",
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Outlined.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(hostState = snackbars) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            ConnectionBanner(
                status = connectionState,
                deviceName = deviceName,
                sessionState = sessionState,
                onOpenConnection = onOpenConnection,
                onDisconnect = { appContainer.connectionRepository.disconnect() },
            )

            if (connectionState == ConnectionStatus.CONNECTED) {
                sessionState.featureStatus.filterValues { it.available == false }.takeIf { it.isNotEmpty() }?.let { unavailable ->
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("Some features need setup", style = MaterialTheme.typography.titleMedium)
                            unavailable.forEach { (key, status) ->
                                Text("• ${prettyFeatureName(key)}: ${status.reason ?: "not ready"}")
                            }
                        }
                    }
                }
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(minSize = 168.dp),
                    modifier = Modifier.fillMaxSize(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(features, key = { it.title }) { item ->
                        FeatureCard(
                            item = item,
                            onUnavailableClick = {
                                scope.launch {
                                    snackbars.showSnackbar(item.statusText ?: "${item.title} is not available yet.")
                                }
                            },
                        )
                    }
                }
            } else {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    ConnectActionCard(
                        title = "USB First",
                        subtitle = "Use ADB reverse when your phone is connected to the PC with USB debugging enabled.",
                        icon = Icons.Outlined.Usb,
                        onClick = onOpenConnection,
                    )
                    ConnectActionCard(
                        title = "Wi-Fi Discovery",
                        subtitle = "Scan the local network, pair with QR, or enter the PC address directly.",
                        icon = Icons.Outlined.Wifi,
                        onClick = onOpenConnection,
                    )
                }
            }
        }
    }
}

@Composable
private fun ConnectionBanner(
    status: ConnectionStatus,
    deviceName: String,
    sessionState: ServerSessionState,
    onOpenConnection: () -> Unit,
    onDisconnect: () -> Unit,
) {
    val color = when (status) {
        ConnectionStatus.CONNECTED -> MaterialTheme.colorScheme.secondary
        ConnectionStatus.CONNECTING -> MaterialTheme.colorScheme.tertiary
        ConnectionStatus.DISCONNECTED -> MaterialTheme.colorScheme.error
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = color.copy(alpha = 0.14f)),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(
                when (status) {
                    ConnectionStatus.CONNECTED -> "Connected to ${deviceName.ifBlank { "your PC" }}"
                    ConnectionStatus.CONNECTING -> "Connecting to your PC..."
                    ConnectionStatus.DISCONNECTED -> "Disconnected"
                },
                style = MaterialTheme.typography.titleMedium,
            )
            if (status == ConnectionStatus.CONNECTED && sessionState.capabilities != null) {
                Text(
                    buildString {
                        append("Server ready: ")
                        append(summaryForCapabilities(sessionState))
                    },
                    style = MaterialTheme.typography.bodyMedium,
                )
                sessionState.featureStatus["usb_bridge"]?.let { usb ->
                    Text(
                        "USB bridge: ${usb.reason ?: if (usb.available == true) "ready" else "not ready"}",
                        style = MaterialTheme.typography.bodySmall,
                        color = if (usb.available == false) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            if (status == ConnectionStatus.CONNECTED) {
                FeatureActionChip("Disconnect", Icons.Outlined.Usb, onDisconnect)
            } else {
                FeatureActionChip("Connect", Icons.Outlined.Wifi, onOpenConnection)
            }
        }
    }
}

@Composable
private fun ConnectActionCard(
    title: String,
    subtitle: String,
    icon: ImageVector,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Row(
            modifier = Modifier.padding(18.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f), RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            }
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(subtitle, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun FeatureActionChip(
    label: String,
    icon: ImageVector,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(50))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(18.dp))
        Text(label)
    }
}

@Composable
private fun FeatureCard(item: FeatureItem, onUnavailableClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = { if (item.enabled) item.onClick() else onUnavailableClick() }),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .background(
                        if (item.enabled) MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)
                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f),
                        RoundedCornerShape(12.dp),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    item.icon,
                    contentDescription = null,
                    tint = if (item.enabled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(item.title, style = MaterialTheme.typography.titleMedium)
            if (!item.enabled || !item.statusText.isNullOrBlank()) {
                Text(
                    item.statusText ?: "Ready",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (item.enabled) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

private data class FeatureItem(
    val title: String,
    val key: String,
    val icon: ImageVector,
    val onClick: () -> Unit,
    val enabled: Boolean = true,
    val statusText: String? = null,
)

private fun resolveFeatureAvailability(state: ServerSessionState, key: String, title: String): Pair<Boolean, String?> {
    val capabilitySupported = when (key) {
        "gamepad" -> state.capabilities?.gamepad ?: false
        "camera" -> state.capabilities?.cameraStreaming ?: false
        "screen_share" -> state.capabilities?.screenStreaming ?: false
        "file_explorer" -> state.capabilities?.fileTransfer ?: false
        "clipboard" -> state.capabilities?.clipboard ?: false
        "task_manager" -> true
        "media_control" -> true
        "touchpad" -> true
        else -> true
    }
    val featureStatus = state.featureStatus[key]
    val available = featureStatus?.available ?: capabilitySupported
    val reason = when {
        featureStatus?.reason?.isNotBlank() == true -> featureStatus.reason
        featureStatus?.supported == false -> "${title} is not supported by this PC."
        !capabilitySupported -> "${title} is disabled on the server."
        featureStatus?.available == false -> "${title} is not ready yet."
        else -> null
    }
    return available to reason
}

private fun summaryForCapabilities(state: ServerSessionState): String {
    val items = buildList {
        if (state.capabilities?.screenStreaming == true) add("screen share")
        if (state.capabilities?.cameraStreaming == true) add("camera")
        if (state.capabilities?.fileTransfer == true) add("file transfer")
        if (state.capabilities?.gamepadAvailable == true) add("gamepad")
        if (state.capabilities?.clipboard == true) add("clipboard")
    }
    return if (items.isEmpty()) "basic input only" else items.joinToString(", ")
}

private fun prettyFeatureName(key: String): String = when (key) {
    "screen_share" -> "Screen Share"
    "file_explorer" -> "File Explorer"
    "media_control" -> "Media Control"
    "task_manager" -> "Task Manager"
    else -> key.replace('_', ' ').replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
}
