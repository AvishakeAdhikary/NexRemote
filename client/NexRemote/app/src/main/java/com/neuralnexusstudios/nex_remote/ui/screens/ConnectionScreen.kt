package com.neuralnexusstudios.nex_remote.ui.screens

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.util.Log
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
import com.composables.ui.components.Text
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
import com.google.android.gms.common.moduleinstall.ModuleInstall
import com.google.android.gms.common.moduleinstall.ModuleInstallRequest
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScanner
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.core.model.ConnectionStatus
import com.neuralnexusstudios.nex_remote.core.model.ServerInfo
import com.neuralnexusstudios.nex_remote.core.network.JsonCodec
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.Keyboard
import androidx.compose.material.icons.outlined.LinkOff
import androidx.compose.ui.Alignment
import androidx.compose.ui.text.input.KeyboardType
import com.composables.ui.components.HorizontalSeparator
import com.composables.ui.components.Icon
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxButton
import com.neuralnexusstudios.nex_remote.ui.design.NxButtonKind
import com.neuralnexusstudios.nex_remote.ui.design.NxCard
import com.neuralnexusstudios.nex_remote.ui.design.NxDialog
import com.neuralnexusstudios.nex_remote.ui.design.NxIconButton
import com.neuralnexusstudios.nex_remote.ui.design.NxIconWell
import com.neuralnexusstudios.nex_remote.ui.design.NxListRow
import com.neuralnexusstudios.nex_remote.ui.design.NxScaffold
import com.neuralnexusstudios.nex_remote.ui.design.NxSectionLabel
import com.neuralnexusstudios.nex_remote.ui.design.NxSnackbarState
import com.neuralnexusstudios.nex_remote.ui.design.NxSpinner
import com.neuralnexusstudios.nex_remote.ui.design.NxStatusPill
import com.neuralnexusstudios.nex_remote.ui.design.NxTextField
import com.neuralnexusstudios.nex_remote.ui.design.NxTone
import com.neuralnexusstudios.nex_remote.ui.design.NxType
import com.neuralnexusstudios.nex_remote.ui.design.rememberNxSnackbarState
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.collectLatest
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Composable
fun ConnectionScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbars = rememberNxSnackbarState()
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

    fun connectScanned(server: ServerInfo) {
        scope.launch { connectToServer(appContainer, server, snackbars, onSuccess = onBack, setConnecting = { connecting = it }) }
    }

    val bundledScanner = rememberLauncherForActivityResult(ScanContract()) { result ->
        val raw = result.contents ?: return@rememberLauncherForActivityResult // cancelled
        parseQrPayload(raw)?.let(::connectScanned) ?: scope.launch { snackbars.showSnackbar(QR_NOT_NEXREMOTE) }
    }

    fun scanQrNow() {
        launchQrScanner(
            context,
            notify = { msg -> scope.launch { snackbars.showSnackbar(msg) } },
            fallback = { bundledScanner.launch(bundledScanOptions()) },
            onResult = ::connectScanned,
        )
    }

    val scanLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            scanQrNow()
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

    LaunchedEffect(appContainer.connectionRepository) {
        appContainer.connectionRepository.events.collectLatest { message ->
            if (message.isNotBlank()) {
                snackbars.showSnackbar(message)
            }
        }
    }

    fun startQrFlow() {
        if (!appContainer.preferences.settings.value.cameraDisclosureAccepted) {
            showDisclosure = true
        } else if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            scanQrNow()
        } else {
            scanLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    NxScaffold(
        title = "Connect",
        onBack = onBack,
        snackbar = snackbars,
        actions = {
            NxIconButton(Icons.Outlined.Refresh, contentDescription = "Search again", onClick = { refreshDiscovery() })
            NxIconButton(Icons.Outlined.QrCodeScanner, contentDescription = "Scan QR code", onClick = { startQrFlow() })
        },
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (connectionState == ConnectionStatus.CONNECTED) {
                item {
                    NxCard(Modifier.fillMaxWidth(), tone = NxTone.Success) {
                        NxStatusPill("Connected", Nx.success)
                        Text("You're connected", style = NxType.headline)
                        Text("This phone is connected to NexRemote on your PC.", style = NxType.body, color = Nx.muted)
                        NxButton("Disconnect", onClick = { appContainer.connectionRepository.disconnect() }, kind = NxButtonKind.Secondary, icon = Icons.Outlined.LinkOff)
                    }
                }
            } else {
                item { NxSectionLabel("On this network") }
                item {
                    NxCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            NxIconWell(Icons.Outlined.Wifi)
                            Column(Modifier.weight(1f)) {
                                Text("Nearby PCs", style = NxType.title)
                                Text(
                                    when {
                                        !appContainer.discoveryRepository.isWifiEnabled() -> "Wi-Fi is off"
                                        discovering -> "Searching…"
                                        servers.isEmpty() -> "None found yet"
                                        else -> "${servers.size} found"
                                    },
                                    style = NxType.bodySmall,
                                    color = Nx.muted,
                                )
                            }
                            if (discovering) NxSpinner(size = 20.dp)
                        }
                        if (!appContainer.discoveryRepository.isWifiEnabled()) {
                            Text("Turn on Wi-Fi to find PCs on your network. USB and direct address still work without it.", style = NxType.bodySmall, color = Nx.muted)
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                NxButton("Wi-Fi settings", onClick = { showWifiPrompt = false; openWifiSettings(context) }, small = true)
                                NxButton("Retry", onClick = { refreshDiscovery() }, kind = NxButtonKind.Outlined, small = true)
                            }
                        } else if (!discovering && servers.isEmpty()) {
                            Text(
                                "Make sure NexRemote is running on your PC and both devices are on the same network. You can also scan its QR code or enter its address.",
                                style = NxType.bodySmall,
                                color = Nx.muted,
                            )
                        }
                        servers.forEach { server ->
                            HorizontalSeparator()
                            NxListRow(
                                title = server.name,
                                subtitle = "${server.address}:${server.port}",
                                icon = Icons.Outlined.Computer,
                                onClick = {
                                    scope.launch { connectToServer(appContainer, server, snackbars, onSuccess = onBack, setConnecting = { connecting = it }) }
                                },
                                trailing = {
                                    if (connecting) NxSpinner(size = 18.dp)
                                    else Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null, tint = Nx.primary, modifier = Modifier.size(18.dp))
                                },
                            )
                        }
                    }
                }

                item { NxSectionLabel("Other ways") }
                item {
                    NxCard(Modifier.fillMaxWidth(), onClick = { startQrFlow() }, contentPadding = PaddingValues(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            NxIconWell(Icons.Outlined.QrCodeScanner)
                            Column(Modifier.weight(1f)) {
                                Text("Scan QR code", style = NxType.title)
                                Text("Scan the code on the NexRemote dashboard on your PC.", style = NxType.bodySmall, color = Nx.muted)
                            }
                            Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null, tint = Nx.muted, modifier = Modifier.size(18.dp))
                        }
                    }
                }
                item {
                    UsbConnectionCard(
                        usbStatus = usbStatus,
                        connecting = connecting,
                        onConnect = {
                            scope.launch {
                                val status = readUsbStatus(context)
                                usbStatus = status
                                if (!(status.connected && status.adbEnabled)) {
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
                                    snackbars.showSnackbar("USB connection failed. Check USB debugging, cable mode and ADB authorization.")
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
                    NxCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            NxIconWell(Icons.Outlined.Keyboard)
                            Column(Modifier.weight(1f)) {
                                Text("Enter address", style = NxType.title)
                                Text("Type the IP shown on the PC dashboard.", style = NxType.bodySmall, color = Nx.muted)
                            }
                        }
                        NxTextField(
                            value = host,
                            onValueChange = { host = it },
                            placeholder = "192.168.1.20",
                            label = "PC address",
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            NxTextField(
                                value = securePort,
                                onValueChange = { securePort = it },
                                label = "Secure port",
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                modifier = Modifier.weight(1f),
                            )
                            NxTextField(
                                value = insecurePort,
                                onValueChange = { insecurePort = it },
                                label = "Fallback port",
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                modifier = Modifier.weight(1f),
                            )
                        }
                        NxButton(
                            if (connecting) "Connecting…" else "Connect",
                            enabled = host.isNotBlank() && !connecting,
                            modifier = Modifier.fillMaxWidth(),
                            onClick = {
                                scope.launch {
                                    connectToServer(
                                        appContainer = appContainer,
                                        server = ServerInfo(
                                            name = host,
                                            address = host.trim(),
                                            port = securePort.toIntOrNull() ?: 8765,
                                            portInsecure = insecurePort.toIntOrNull() ?: 8766,
                                        ),
                                        snackbars = snackbars,
                                        onSuccess = onBack,
                                        setConnecting = { connecting = it },
                                    )
                                }
                            },
                        )
                    }
                }
            }
        }
    }

    if (showDisclosure) {
        NxDialog(
            onDismissRequest = { showDisclosure = false },
            icon = Icons.Outlined.QrCodeScanner,
            title = "Camera for QR pairing",
            text = {
                Text(
                    "NexRemote uses the camera only when you choose QR pairing, to read the connection code shown by NexRemote on your PC. Camera data is not stored or sent to Neural Nexus Studios.",
                    style = NxType.body,
                    color = Nx.muted,
                )
            },
            confirmButton = {
                NxButton("Continue", onClick = {
                    showDisclosure = false
                    appContainer.preferences.setCameraDisclosureAccepted()
                    startQrFlow()
                })
            },
            dismissButton = { NxButton("Cancel", onClick = { showDisclosure = false }, kind = NxButtonKind.Ghost) },
        )
    }

    if (showWifiPrompt) {
        NxDialog(
            onDismissRequest = { showWifiPrompt = false },
            icon = Icons.Outlined.Wifi,
            title = "Turn on Wi-Fi",
            text = { Text("Finding PCs needs Wi-Fi. You can still use USB or enter the PC's address.", style = NxType.body, color = Nx.muted) },
            confirmButton = {
                NxButton("Open settings", onClick = {
                    showWifiPrompt = false
                    openWifiSettings(context)
                })
            },
            dismissButton = { NxButton("Later", onClick = { showWifiPrompt = false }, kind = NxButtonKind.Ghost) },
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
    val ready = usbStatus.connected && usbStatus.adbEnabled
    NxCard(Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            NxIconWell(Icons.Outlined.Usb)
            Column(Modifier.weight(1f)) {
                Text("USB", style = NxType.title)
                Text("Lowest latency. Uses ADB reverse.", style = NxType.bodySmall, color = Nx.muted)
            }
            NxStatusPill(
                when {
                    ready -> "Ready"
                    usbStatus.connected -> "Needs setup"
                    else -> "Unplugged"
                },
                when {
                    ready -> Nx.success
                    usbStatus.connected -> Nx.warning
                    else -> Nx.muted
                },
            )
        }
        Text(
            when {
                ready -> "USB debugging is on. Connect while NexRemote is running on your PC."
                usbStatus.connected -> "Turn on USB debugging, accept the prompt on this phone, and use a data cable."
                else -> "Plug this phone into your PC with USB debugging turned on."
            },
            style = NxType.bodySmall,
            color = Nx.muted,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NxButton(if (connecting) "Connecting…" else "Connect via USB", onClick = onConnect, enabled = !connecting, small = true)
            NxButton("Setup guide", onClick = onGuide, kind = NxButtonKind.Outlined, icon = Icons.Outlined.Settings, small = true)
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
    NxDialog(
        onDismissRequest = onDismiss,
        icon = Icons.Outlined.Usb,
        title = "Set up USB",
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("USB mode connects through ADB reverse to NexRemote on your PC.", style = NxType.body, color = Nx.muted)
                Text("Status: ${usbStatus.describe()}", style = NxType.label, color = Nx.primary)
                listOf(
                    "Turn on Developer options (tap Build number 7 times).",
                    "Turn on USB debugging.",
                    "Use a data cable; pick File transfer if asked.",
                    "Accept the USB debugging prompt on this phone.",
                    "Keep NexRemote running on the PC.",
                ).forEachIndexed { i, step -> Text("${i + 1}. $step", style = NxType.bodySmall) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    NxButton("Developer options", onClick = onOpenDeveloperOptions, kind = NxButtonKind.Outlined, small = true)
                    NxButton("About phone", onClick = onOpenDeviceInfo, kind = NxButtonKind.Outlined, small = true)
                }
            }
        },
        confirmButton = { NxButton("Retry USB", onClick = onRetry) },
        dismissButton = { NxButton("Close", onClick = onDismiss, kind = NxButtonKind.Ghost) },
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

private const val QR_TAG = "NexRemoteQr"
private const val QR_NOT_NEXREMOTE = "That QR code isn't from NexRemote. Scan the code on the NexRemote dashboard on your PC."

private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

/**
 * Scans the PC's pairing QR code.
 *
 * Google's code scanner is preferred (no camera code in the app), but it lives in Google Play
 * services as an optional module that may not be downloaded yet, may be stuck downloading, or may
 * not exist at all (phones without Play services). In every one of those cases, fall back to the
 * bundled ZXing scanner, and ask Play services to fetch its module for next time.
 */
private fun launchQrScanner(
    context: Context,
    notify: (String) -> Unit,
    fallback: () -> Unit,
    onResult: (ServerInfo) -> Unit,
) {
    val activity = context.findActivity() ?: return fallback()
    val options = GmsBarcodeScannerOptions.Builder()
        .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
        .build()
    val scanner = runCatching { GmsBarcodeScanning.getClient(activity, options) }.getOrElse {
        Log.w(QR_TAG, "Google code scanner unavailable, using the built-in scanner", it)
        return fallback()
    }
    val modules = ModuleInstall.getClient(activity)
    modules.areModulesAvailable(scanner)
        .addOnSuccessListener { availability ->
            if (availability.areModulesAvailable()) {
                startGoogleScan(scanner, notify, fallback, onResult)
            } else {
                modules.installModules(ModuleInstallRequest.newBuilder().addApi(scanner).build())
                    .addOnFailureListener { Log.w(QR_TAG, "Scanner module install request failed", it) }
                fallback()
            }
        }
        .addOnFailureListener {
            Log.w(QR_TAG, "Play services can't check the scanner module, using the built-in scanner", it)
            fallback()
        }
}

private fun startGoogleScan(
    scanner: GmsBarcodeScanner,
    notify: (String) -> Unit,
    fallback: () -> Unit,
    onResult: (ServerInfo) -> Unit,
) {
    scanner.startScan()
        .addOnSuccessListener { barcode ->
            parseQrPayload(barcode.rawValue.orEmpty())?.let(onResult) ?: notify(QR_NOT_NEXREMOTE)
        }
        .addOnFailureListener {
            // e.g. "Waiting for the Barcode UI module to be downloaded" although the module check passed.
            Log.w(QR_TAG, "Google code scanner failed, using the built-in scanner", it)
            fallback()
        }
}

internal fun bundledScanOptions(): ScanOptions = ScanOptions()
    .setDesiredBarcodeFormats(ScanOptions.QR_CODE)
    .setPrompt("Point the camera at the QR code on the NexRemote dashboard on your PC")
    .setBeepEnabled(false)
    .setOrientationLocked(false)
internal fun parseQrPayload(raw: String): ServerInfo? = runCatching {
    val payload = JsonCodec.parseToJsonElement(raw).jsonObject
    val host = payload["host"]?.jsonPrimitive?.contentOrNull.orEmpty()
    if (host.isBlank()) return null
    ServerInfo(
        name = payload["name"]?.jsonPrimitive?.contentOrNull ?: "PC",
        address = host,
        port = payload["port"]?.jsonPrimitive?.intOrNull ?: 8765,
        portInsecure = payload["port_insecure"]?.jsonPrimitive?.intOrNull ?: 8766,
        id = payload["id"]?.jsonPrimitive?.contentOrNull.orEmpty(),
        certificateFingerprint = payload["cert_fingerprint"]?.jsonPrimitive?.contentOrNull
            ?: payload["certificate_fingerprint"]?.jsonPrimitive?.contentOrNull,
    )
}.getOrNull()

private suspend fun connectToServer(
    appContainer: AppContainer,
    server: ServerInfo,
    snackbars: NxSnackbarState,
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
