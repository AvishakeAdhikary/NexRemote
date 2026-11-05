package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.automirrored.outlined.ScreenShare
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.Folder
import androidx.compose.material.icons.outlined.Gamepad
import androidx.compose.material.icons.outlined.LinkOff
import androidx.compose.material.icons.outlined.MusicNote
import androidx.compose.material.icons.outlined.PhonelinkRing
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.TaskAlt
import androidx.compose.material.icons.outlined.TouchApp
import androidx.compose.material.icons.outlined.Usb
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.composables.ui.components.Icon
import com.composables.ui.components.Text
import com.neuralnexusstudios.nex_remote.R
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.core.model.ConnectionStatus
import com.neuralnexusstudios.nex_remote.core.model.ServerSessionState
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxButton
import com.neuralnexusstudios.nex_remote.ui.design.NxButtonKind
import com.neuralnexusstudios.nex_remote.ui.design.NxCard
import com.neuralnexusstudios.nex_remote.ui.design.NxIconButton
import com.neuralnexusstudios.nex_remote.ui.design.NxIconWell
import com.neuralnexusstudios.nex_remote.ui.design.NxScaffold
import com.neuralnexusstudios.nex_remote.ui.design.NxSectionLabel
import com.neuralnexusstudios.nex_remote.ui.design.NxSpinner
import com.neuralnexusstudios.nex_remote.ui.design.NxStatusPill
import com.neuralnexusstudios.nex_remote.ui.design.NxTone
import com.neuralnexusstudios.nex_remote.ui.design.NxType
import com.neuralnexusstudios.nex_remote.ui.design.rememberNxSnackbarState
import kotlinx.coroutines.launch

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
    onOpenPhoneShare: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val snackbars = rememberNxSnackbarState()
    val connectionState by appContainer.connectionRepository.connectionState.collectAsState()
    val deviceName by appContainer.connectionRepository.connectedDeviceName.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()

    val features = listOf(
        FeatureItem("Touchpad", "Mouse & keyboard", "touchpad", Icons.Outlined.TouchApp, onOpenTouchpad),
        FeatureItem("Gamepad", "Virtual controller", "gamepad", Icons.Outlined.Gamepad, onOpenGamepad),
        FeatureItem("Screen", "View & control PC", "screen_share", Icons.AutoMirrored.Outlined.ScreenShare, onOpenScreenShare),
        FeatureItem("Share my screen", "Phone to PC", "phone_screen", Icons.Outlined.PhonelinkRing, onOpenPhoneShare),
        FeatureItem("Media", "Playback & volume", "media_control", Icons.Outlined.MusicNote, onOpenMedia),
        FeatureItem("Camera", "PC webcams", "camera", Icons.Outlined.CameraAlt, onOpenCamera),
        FeatureItem("Files", "Browse the PC", "file_explorer", Icons.Outlined.Folder, onOpenFileExplorer),
        FeatureItem("Tasks", "Processes & stats", "task_manager", Icons.Outlined.TaskAlt, onOpenTaskManager),
    ).map { feature ->
        val availability = resolveFeatureAvailability(sessionState, feature.key, feature.title)
        feature.copy(enabled = availability.first, statusText = availability.second)
    }

    NxScaffold(
        title = "NexRemote",
        snackbar = snackbars,
        titleContent = {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Image(
                    painter = painterResource(R.drawable.ic_launcher_foreground),
                    contentDescription = null,
                    modifier = Modifier.size(40.dp),
                )
                Text("NexRemote", style = NxType.headline)
            }
        },
        actions = {
            NxIconButton(Icons.Outlined.Settings, contentDescription = "Settings", onClick = onOpenSettings)
        },
    ) {
        LazyVerticalGrid(
            columns = GridCells.Adaptive(minSize = 156.dp),
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item(span = { GridItemSpan(maxLineSpan) }) {
                ConnectionHero(
                    status = connectionState,
                    deviceName = deviceName,
                    sessionState = sessionState,
                    onOpenConnection = onOpenConnection,
                    onDisconnect = { appContainer.connectionRepository.disconnect() },
                )
            }

            if (connectionState == ConnectionStatus.CONNECTED) {
                val unavailable = sessionState.featureStatus.filter { (key, status) -> key != "usb_bridge" && status.available == false }
                if (unavailable.isNotEmpty()) {
                    item(span = { GridItemSpan(maxLineSpan) }) {
                        NxCard(Modifier.fillMaxWidth(), tone = NxTone.Warning) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                Icon(Icons.Outlined.WarningAmber, contentDescription = null, tint = Nx.warning, modifier = Modifier.size(20.dp))
                                Text("Some features need setup on the PC", style = NxType.titleSmall)
                            }
                            unavailable.forEach { (key, status) ->
                                Text("${prettyFeatureName(key)}: ${status.reason ?: "not ready"}", style = NxType.bodySmall, color = Nx.muted)
                            }
                        }
                    }
                }
                item(span = { GridItemSpan(maxLineSpan) }) { NxSectionLabel("Controls") }
                items(features, key = { it.key }) { item ->
                    FeatureTile(
                        item = item,
                        onUnavailableClick = {
                            scope.launch { snackbars.showSnackbar(item.statusText ?: "${item.title} is not available yet.") }
                        },
                    )
                }
            } else {
                item(span = { GridItemSpan(maxLineSpan) }) { NxSectionLabel("Ways to connect") }
                item(span = { GridItemSpan(maxLineSpan) }) {
                    ConnectOption(
                        title = "Wi-Fi",
                        subtitle = "Find your PC on this network, or enter its address.",
                        icon = Icons.Outlined.Wifi,
                        onClick = onOpenConnection,
                    )
                }
                item(span = { GridItemSpan(maxLineSpan) }) {
                    ConnectOption(
                        title = "Scan QR code",
                        subtitle = "Open NexRemote on your PC and scan the code on its dashboard.",
                        icon = Icons.Outlined.QrCodeScanner,
                        onClick = onOpenConnection,
                    )
                }
                item(span = { GridItemSpan(maxLineSpan) }) {
                    ConnectOption(
                        title = "USB",
                        subtitle = "Plug in with USB debugging on for the lowest latency.",
                        icon = Icons.Outlined.Usb,
                        onClick = onOpenConnection,
                    )
                }
                item(span = { GridItemSpan(maxLineSpan) }) {
                    Text(
                        "Get NexRemote for Windows from the Microsoft Store. Everything stays between your phone and your PC.",
                        style = NxType.bodySmall,
                        color = Nx.muted,
                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 8.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun ConnectionHero(
    status: ConnectionStatus,
    deviceName: String,
    sessionState: ServerSessionState,
    onOpenConnection: () -> Unit,
    onDisconnect: () -> Unit,
) {
    val shape = RoundedCornerShape(26.dp)
    val glow = when (status) {
        ConnectionStatus.CONNECTED -> Nx.primary.copy(alpha = 0.28f)
        ConnectionStatus.CONNECTING -> Nx.warning.copy(alpha = 0.18f)
        ConnectionStatus.DISCONNECTED -> Nx.primary.copy(alpha = 0.12f)
    }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(Brush.linearGradient(listOf(glow, Nx.panel, Nx.panel)))
            .border(1.dp, Nx.border, shape)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        when (status) {
            ConnectionStatus.CONNECTED -> NxStatusPill("Connected", Nx.success)
            ConnectionStatus.CONNECTING -> Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NxSpinner(size = 16.dp, color = Nx.warning)
                Text("Connecting", style = NxType.label, color = Nx.warning)
            }
            ConnectionStatus.DISCONNECTED -> NxStatusPill("Not connected", Nx.muted)
        }
        Text(
            when (status) {
                ConnectionStatus.CONNECTED -> deviceName.ifBlank { "Your PC" }
                ConnectionStatus.CONNECTING -> "Reaching your PC…"
                ConnectionStatus.DISCONNECTED -> "Control your PC from here"
            },
            style = NxType.display,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        if (status == ConnectionStatus.CONNECTED && sessionState.capabilities != null) {
            Text(summaryForCapabilities(sessionState), style = NxType.bodySmall, color = Nx.muted)
            sessionState.featureStatus["usb_bridge"]?.let { usb ->
                Text(
                    "USB bridge: ${usb.reason ?: if (usb.available == true) "ready" else "not ready"}",
                    style = NxType.bodySmall,
                    color = if (usb.available == false) Nx.warning else Nx.muted,
                )
            }
        } else if (status == ConnectionStatus.DISCONNECTED) {
            Text("Pair with NexRemote on your Windows PC over Wi-Fi or USB.", style = NxType.body, color = Nx.muted)
        }
        Spacer(Modifier.height(4.dp))
        if (status == ConnectionStatus.CONNECTED) {
            NxButton("Disconnect", onClick = onDisconnect, kind = NxButtonKind.Secondary, icon = Icons.Outlined.LinkOff)
        } else {
            NxButton(
                if (status == ConnectionStatus.CONNECTING) "Connection options" else "Connect to a PC",
                onClick = onOpenConnection,
                icon = Icons.AutoMirrored.Outlined.ArrowForward,
            )
        }
    }
}

@Composable
private fun ConnectOption(title: String, subtitle: String, icon: ImageVector, onClick: () -> Unit) {
    NxCard(Modifier.fillMaxWidth(), onClick = onClick, contentPadding = PaddingValues(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            NxIconWell(icon)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, style = NxType.title)
                Text(subtitle, style = NxType.bodySmall, color = Nx.muted)
            }
            Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null, tint = Nx.muted, modifier = Modifier.size(18.dp))
        }
    }
}

@Composable
private fun FeatureTile(item: FeatureItem, onUnavailableClick: () -> Unit) {
    NxCard(
        modifier = Modifier
            .fillMaxWidth()
            .height(148.dp)
            .alpha(if (item.enabled) 1f else 0.6f),
        onClick = { if (item.enabled) item.onClick() else onUnavailableClick() },
        contentPadding = PaddingValues(16.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
            NxIconWell(item.icon, active = item.enabled, size = 46.dp)
            Spacer(Modifier.weight(1f))
            if (!item.enabled) {
                Box(Modifier.size(8.dp).clip(CircleShape).background(Nx.warning))
            }
        }
        Spacer(Modifier.weight(1f))
        Text(item.title, style = NxType.title, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(
            if (item.enabled) item.subtitle else (item.statusText ?: "Not available"),
            style = NxType.bodySmall,
            color = if (item.enabled) Nx.muted else Nx.warning,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

private data class FeatureItem(
    val title: String,
    val subtitle: String,
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
        "phone_screen" -> state.capabilities?.phoneScreen ?: false
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
        featureStatus?.supported == false -> "$title is not supported by this PC."
        key == "phone_screen" && !capabilitySupported -> "Update NexRemote on your PC to share this phone's screen."
        !capabilitySupported -> "$title is disabled on the server."
        featureStatus?.available == false -> "$title is not ready yet."
        else -> null
    }
    return available to reason
}

private fun summaryForCapabilities(state: ServerSessionState): String {
    val items = buildList {
        if (state.capabilities?.screenStreaming == true) add("screen share")
        if (state.capabilities?.cameraStreaming == true) add("camera")
        if (state.capabilities?.fileTransfer == true) add("files")
        if (state.capabilities?.gamepadAvailable == true) add("gamepad")
        if (state.capabilities?.clipboard == true) add("clipboard")
        if (state.capabilities?.phoneScreen == true) add("phone screen")
    }
    return if (items.isEmpty()) "Basic input only" else "Ready: " + items.joinToString(" · ")
}

private fun prettyFeatureName(key: String): String = when (key) {
    "screen_share" -> "Screen share"
    "file_explorer" -> "Files"
    "media_control" -> "Media"
    "task_manager" -> "Tasks"
    "phone_screen" -> "Share my screen"
    else -> key.replace('_', ' ').replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
}

