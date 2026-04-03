package com.neuralnexusstudios.nexremote.ui.screens

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Computer
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Usb
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.core.model.ConnectionStatus
import com.neuralnexusstudios.nexremote.core.model.ServerInfo
import com.neuralnexusstudios.nexremote.core.network.JsonCodec
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar
import kotlinx.coroutines.launch
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConnectionScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbars = remember { SnackbarHostState() }
    val servers = remember { mutableStateListOf<ServerInfo>() }
    val connectionState by appContainer.connectionRepository.connectionState.collectAsState()
    var discovering by remember { mutableStateOf(false) }
    var connecting by remember { mutableStateOf(false) }
    var host by remember { mutableStateOf("") }
    var securePort by remember { mutableStateOf("8765") }
    var insecurePort by remember { mutableStateOf("8766") }
    var showDisclosure by remember { mutableStateOf(false) }
    var showWifiPrompt by remember { mutableStateOf(false) }
    var showUsbGuide by remember { mutableStateOf(false) }
    var usbStatus by remember { mutableStateOf(readUsbStatus(context)) }

    val scanLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            launchQrScanner(context, snackbars, onResult = { server ->
                scope.launch { connectToServer(appContainer, server, snackbars, onSuccess = onBack, setConnecting = { connecting = it }) }
            })
        } else {
            scope.launch { snackbars.showSnackbar("Camera permission is required to scan a QR code.") }
        }
    }

    fun refreshUsbStatus() {
        usbStatus = readUsbStatus(context)
    }

    fun refreshDiscovery() {
        scope.launch {
            refreshUsbStatus()
            if (!appContainer.discoveryRepository.isWifiEnabled()) {
                showWifiPrompt = true
                discovering = false
                servers.clear()
                return@launch
            }
            discovering = true
            servers.clear()
            servers += appContainer.discoveryRepository.discoverServers()
            discovering = false
            if (servers.isEmpty()) {
                snackbars.showSnackbar("No PCs found. Try USB, QR scanning, or direct host entry.")
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshDiscovery()
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = "Connect to PC",
                onBack = onBack,
                actions = {
                    IconButton(onClick = { refreshDiscovery() }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Refresh")
                    }
                    IconButton(onClick = {
                        if (!appContainer.preferences.settings.value.cameraDisclosureAccepted) {
                            showDisclosure = true
                        } else {
                            if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                                launchQrScanner(context, snackbars, onResult = { server ->
                                    scope.launch {
                                        connectToServer(appContainer, server, snackbars, onSuccess = onBack, setConnecting = { connecting = it })
                                    }
                                })
                            } else {
                                scanLauncher.launch(Manifest.permission.CAMERA)
                            }
                        }
                    }) {
                        Icon(Icons.Outlined.QrCodeScanner, contentDescription = "Scan QR")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(hostState = snackbars) },
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (connectionState == ConnectionStatus.CONNECTED) {
                item {
                    Card {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Text("Connection active", style = MaterialTheme.typography.titleMedium)
                            Text("Your phone is already connected to the NexRemote PC server.")
                            Button(onClick = { appContainer.connectionRepository.disconnect() }) {
                                Text("Disconnect")
                            }
                        }
                    }
                }
            } else {
                item {
                    UsbConnectionCard(
                        usbStatus = usbStatus,
                        connecting = connecting,
                    onConnect = {
                        scope.launch {
                            val status = readUsbStatus(context)
                            usbStatus = status
                            val ready = status.connected && status.adbEnabled
                            if (!ready) {
                                showUsbGuide = true
                                return@launch
                            }
                                connecting = true
                                val success = runCatching { appContainer.connectionRepository.connectUsb() }.getOrDefault(false)
                                connecting = false
                                if (success) {
                                    onBack()
                                } else {
                                    showUsbGuide = true
                                    snackbars.showSnackbar("USB connection failed. Check USB debugging, cable mode, and ADB authorization.")
                                }
                            }
                        },
                        onGuide = {
                            refreshUsbStatus()
                            showUsbGuide = true
                        },
                    )
                }

                item {
                    Card {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Icon(Icons.Outlined.Wifi, contentDescription = null)
                                Text("Wi-Fi and QR", style = MaterialTheme.typography.titleMedium)
                            }
                            if (!appContainer.discoveryRepository.isWifiEnabled()) {
                                Text("Wi-Fi is off. Turn it on to scan your local network for PCs.")
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Button(onClick = {
                                        showWifiPrompt = false
                                        openWifiSettings(context)
                                    }) {
                                        Text("Open Wi-Fi Settings")
                                    }
                                    OutlinedButton(onClick = { refreshDiscovery() }) {
                                        Text("Retry")
                                    }
                                }
                            } else if (discovering) {
                                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    CircularProgressIndicator()
                                    Text("Searching for PCs on your network...")
                                }
                            } else if (servers.isEmpty()) {
                                Text("No PCs found yet. You can retry discovery, scan a QR code, or use direct host entry.")
                            } else {
                                Text("Discovered PCs", style = MaterialTheme.typography.titleSmall)
                            }
                        }
                    }
                }

                items(servers, key = { it.id.ifBlank { it.address } }) { server ->
                    Card(modifier = Modifier.fillMaxWidth().clickable {
                        scope.launch {
                            connectToServer(appContainer, server, snackbars, onSuccess = onBack, setConnecting = { connecting = it })
                        }
                    }) {
                        Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Icon(Icons.Outlined.Computer, contentDescription = null)
                            Column {
                                Text(server.name, style = MaterialTheme.typography.titleMedium)
                                Text("${server.address}:${server.port}", style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                }

                item {
                    Card {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Text("Direct connection", style = MaterialTheme.typography.titleMedium)
                            OutlinedTextField(value = host, onValueChange = { host = it }, label = { Text("Host / IP") }, modifier = Modifier.fillMaxWidth())
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                OutlinedTextField(value = securePort, onValueChange = { securePort = it }, label = { Text("Secure Port") }, modifier = Modifier.weight(1f))
                                OutlinedTextField(value = insecurePort, onValueChange = { insecurePort = it }, label = { Text("Insecure Port") }, modifier = Modifier.weight(1f))
                            }
                            Button(
                                enabled = host.isNotBlank() && !connecting,
                                onClick = {
                                    scope.launch {
                                        connectToServer(
                                            appContainer = appContainer,
                                            server = ServerInfo(
                                                name = host,
                                                address = host,
                                                port = securePort.toIntOrNull() ?: 8765,
                                                portInsecure = insecurePort.toIntOrNull() ?: 8766,
                                            ),
                                            snackbars = snackbars,
                                            onSuccess = onBack,
                                            setConnecting = { connecting = it },
                                        )
                                    }
                                },
                            ) {
                                Text(if (connecting) "Connecting..." else "Connect")
                            }
                        }
                    }
                }
            }
        }
    }

    if (showDisclosure) {
        AlertDialog(
            onDismissRequest = { showDisclosure = false },
            title = { Text("Camera Disclosure") },
            text = {
                Text(
                    "NexRemote uses the camera only when you choose QR pairing so it can read a connection code shown by the NexRemote PC app. Camera data is not stored or sent to Neural Nexus Studios.",
                )
            },
            confirmButton = {
                Button(onClick = {
                    showDisclosure = false
                    appContainer.preferences.setCameraDisclosureAccepted()
                    if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                        launchQrScanner(context, snackbars, onResult = { server ->
                            scope.launch { connectToServer(appContainer, server, snackbars, onSuccess = onBack, setConnecting = { connecting = it }) }
                        })
                    } else {
                        scanLauncher.launch(Manifest.permission.CAMERA)
                    }
                }) {
                    Text("Continue")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showDisclosure = false }) {
                    Text("Cancel")
                }
            },
        )
    }

    if (showWifiPrompt) {
        AlertDialog(
            onDismissRequest = { showWifiPrompt = false },
            title = { Text("Turn on Wi-Fi") },
            text = { Text("Wi-Fi discovery needs Wi-Fi enabled. You can still use USB or a direct host entry without it.") },
            confirmButton = {
                Button(onClick = {
                    showWifiPrompt = false
                    openWifiSettings(context)
                }) {
                    Text("Open Settings")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showWifiPrompt = false }) {
                    Text("Later")
                }
            },
        )
    }

    if (showUsbGuide) {
        UsbGuideDialog(
            usbStatus = usbStatus,
            onDismiss = { showUsbGuide = false },
            onOpenDeveloperOptions = { openSettingsIntent(context, Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS) },
            onOpenDeviceInfo = { openSettingsIntent(context, Settings.ACTION_DEVICE_INFO_SETTINGS) },
            onRetry = {
                scope.launch {
                    val status = readUsbStatus(context)
                    usbStatus = status
                    if (!(status.connected && status.adbEnabled)) {
                        showUsbGuide = true
                        return@launch
                    }
                    showUsbGuide = false
                    connecting = true
                    val success = runCatching { appContainer.connectionRepository.connectUsb() }.getOrDefault(false)
                    connecting = false
                    if (success) onBack() else showUsbGuide = true
                }
            },
        )
    }
}

@Composable
private fun UsbConnectionCard(
    usbStatus: UsbStatus,
    connecting: Boolean,
    onConnect: () -> Unit,
    onGuide: () -> Unit,
) {
    Card {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Outlined.Usb, contentDescription = null)
                Text("USB (ADB Reverse)", style = MaterialTheme.typography.titleMedium)
            }
            Text(
                when {
                    usbStatus.connected && usbStatus.adbEnabled ->
                        "USB detected and ADB looks available. This is the fastest path when the cable is ready."
                    usbStatus.connected ->
                        "USB is connected, but ADB debugging is not ready yet. Enable USB debugging, accept the RSA prompt, and prefer a data-capable cable/mode."
                    else ->
                        "Connect your phone to the PC, enable USB debugging, and keep NexRemote Server running on the PC."
                },
            )
            Text(
                "Status: ${usbStatus.describe()}",
                style = MaterialTheme.typography.bodySmall,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onConnect, enabled = !connecting) {
                    Text(if (connecting) "Connecting..." else "Connect via USB")
                }
                OutlinedButton(onClick = onGuide) {
                    Icon(Icons.Outlined.Settings, contentDescription = null)
                    Text("Setup Guide", modifier = Modifier.padding(start = 8.dp))
                }
            }
        }
    }
}

@Composable
private fun UsbGuideDialog(
    usbStatus: UsbStatus,
    onDismiss: () -> Unit,
    onOpenDeveloperOptions: () -> Unit,
    onOpenDeviceInfo: () -> Unit,
    onRetry: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("USB Setup Required") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("NexRemote USB mode uses ADB reverse to connect to your PC server through localhost.")
                Text("Current USB status: ${usbStatus.describe()}", style = MaterialTheme.typography.bodySmall)
                Text("1. Enable Developer Options")
                Text("2. Enable USB Debugging")
                Text("3. Use a data-capable USB cable and a mode like File Transfer when needed")
                Text("4. Accept the USB debugging authorization prompt")
                Text("5. Keep the NexRemote PC server running so it can set up ADB reverse")
            }
        },
        confirmButton = {
            Button(onClick = onRetry) {
                Text("Retry USB")
            }
        },
        dismissButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onOpenDeveloperOptions) {
                    Text("Developer Options")
                }
                OutlinedButton(onClick = onOpenDeviceInfo) {
                    Text("Build Info")
                }
            }
        },
    )
}

private fun readUsbStatus(context: Context): UsbStatus {
    val intent = context.registerReceiver(null, IntentFilter("android.hardware.usb.action.USB_STATE"))
    return UsbStatus(
        connected = intent?.getBooleanExtra("connected", false) ?: false,
        configured = intent?.getBooleanExtra("configured", false) ?: false,
        adbEnabled = intent?.getBooleanExtra("adb", false) ?: false,
        mtp = intent?.getBooleanExtra("mtp", false) ?: false,
        ptp = intent?.getBooleanExtra("ptp", false) ?: false,
    )
}

private fun openWifiSettings(context: Context) {
    val action = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        Settings.Panel.ACTION_WIFI
    } else {
        Settings.ACTION_WIFI_SETTINGS
    }
    openSettingsIntent(context, action)
}

private fun openSettingsIntent(context: Context, action: String) {
    runCatching {
        context.startActivity(Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}

private fun launchQrScanner(
    context: Context,
    snackbars: SnackbarHostState,
    onResult: (ServerInfo) -> Unit,
) {
    val options = GmsBarcodeScannerOptions.Builder()
        .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
        .build()
    val scanner = GmsBarcodeScanning.getClient(context, options)
    scanner.startScan()
        .addOnSuccessListener { barcode ->
            val raw = barcode.rawValue.orEmpty()
            runCatching {
                val payload = JsonCodec.parseToJsonElement(raw).jsonObject
                onResult(
                    ServerInfo(
                        name = payload["name"]?.jsonPrimitive?.contentOrNull ?: "PC",
                        address = payload["host"]?.jsonPrimitive?.contentOrNull ?: "",
                        port = payload["port"]?.jsonPrimitive?.intOrNull ?: 8765,
                        portInsecure = payload["port_insecure"]?.jsonPrimitive?.intOrNull ?: 8766,
                        id = payload["id"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                    ),
                )
            }.onFailure {
                snackbars.currentSnackbarData?.dismiss()
            }
        }
        .addOnFailureListener {
            snackbars.currentSnackbarData?.dismiss()
        }
}

private suspend fun connectToServer(
    appContainer: AppContainer,
    server: ServerInfo,
    snackbars: SnackbarHostState,
    onSuccess: () -> Unit,
    setConnecting: (Boolean) -> Unit,
) {
    setConnecting(true)
    val success = appContainer.connectionRepository.connect(server)
    setConnecting(false)
    if (success) {
        onSuccess()
    } else {
        snackbars.showSnackbar("Failed to connect to ${server.name}.")
    }
}

private data class UsbStatus(
    val connected: Boolean,
    val configured: Boolean,
    val adbEnabled: Boolean,
    val mtp: Boolean,
    val ptp: Boolean,
) {
    fun describe(): String = buildList {
        if (connected) add("connected") else add("not connected")
        if (configured) add("configured")
        if (adbEnabled) add("adb ready")
        if (mtp) add("file transfer")
        if (ptp) add("photo transfer")
    }.joinToString(", ")
}
