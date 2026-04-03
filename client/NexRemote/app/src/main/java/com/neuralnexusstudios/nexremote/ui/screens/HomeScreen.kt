package com.neuralnexusstudios.nexremote.ui.screens

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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.core.model.ConnectionStatus
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar

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
    val connectionState by appContainer.connectionRepository.connectionState.collectAsState()
    val deviceName by appContainer.connectionRepository.connectedDeviceName.collectAsState()

    val features = listOf(
        FeatureItem("Gamepad", Icons.Outlined.Gamepad, onOpenGamepad),
        FeatureItem("Touchpad", Icons.Outlined.TouchApp, onOpenTouchpad),
        FeatureItem("Media Control", Icons.Outlined.MusicNote, onOpenMedia),
        FeatureItem("Camera", Icons.Outlined.CameraAlt, onOpenCamera),
        FeatureItem("Screen Share", Icons.AutoMirrored.Outlined.ScreenShare, onOpenScreenShare),
        FeatureItem("File Explorer", Icons.Outlined.Folder, onOpenFileExplorer),
        FeatureItem("Task Manager", Icons.Outlined.TaskAlt, onOpenTaskManager),
    )

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
                onOpenConnection = onOpenConnection,
                onDisconnect = { appContainer.connectionRepository.disconnect() },
            )

            if (connectionState == ConnectionStatus.CONNECTED) {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(minSize = 168.dp),
                    modifier = Modifier.fillMaxSize(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(features, key = { it.title }) { item ->
                        FeatureCard(item)
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
private fun FeatureCard(item: FeatureItem) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = item.onClick),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(item.icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            }
            Text(item.title, style = MaterialTheme.typography.titleMedium)
        }
    }
}

private data class FeatureItem(
    val title: String,
    val icon: ImageVector,
    val onClick: () -> Unit,
)
