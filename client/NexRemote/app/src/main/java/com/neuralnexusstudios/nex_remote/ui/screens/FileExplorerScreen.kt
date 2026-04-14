package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.collectAsState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.InsertDriveFile
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.outlined.NoteAdd
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Archive
import androidx.compose.material.icons.outlined.AudioFile
import androidx.compose.material.icons.outlined.ContentPaste
import androidx.compose.material.icons.outlined.CreateNewFolder
import androidx.compose.material.icons.outlined.DataObject
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Folder
import androidx.compose.material.icons.outlined.Image
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.PictureAsPdf
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.SyncAlt
import androidx.compose.material.icons.outlined.TextFields
import androidx.compose.material.icons.outlined.UploadFile
import androidx.compose.material.icons.outlined.VideoFile
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.core.feature.FileExplorerEvent
import com.neuralnexusstudios.nex_remote.core.model.DriveInfo
import com.neuralnexusstudios.nex_remote.core.model.FileItem
import com.neuralnexusstudios.nex_remote.core.model.FileProperties
import com.neuralnexusstudios.nex_remote.ui.components.AppTopBar

private data class EditorState(
    val path: String,
    val name: String,
    val originalContent: String,
    val currentContent: String,
)

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun FileExplorerScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val snackbars = remember { SnackbarHostState() }
    val files = remember { mutableStateListOf<FileItem>() }
    val drives = remember { mutableStateListOf<DriveInfo>() }
    val history = remember { mutableStateListOf("C:\\") }
    var currentPath by remember { mutableStateOf("C:\\") }
    var search by remember { mutableStateOf("") }
    var editorState by remember { mutableStateOf<EditorState?>(null) }
    var showLineNumbers by remember { mutableStateOf(true) }
    var showingProperties by remember { mutableStateOf<FileProperties?>(null) }
    var renameItem by remember { mutableStateOf<FileItem?>(null) }
    var createType by remember { mutableStateOf<String?>(null) }
    var clipboardPath by remember { mutableStateOf<String?>(null) }
    var clipboardCut by remember { mutableStateOf(false) }
    var confirmDiscard by remember { mutableStateOf(false) }
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    val fileTransferAvailable = sessionState.connected &&
        sessionState.capabilities?.fileTransfer != false &&
        sessionState.featureStatus["file_explorer"]?.available != false
    val fileTransferReason = sessionState.featureStatus["file_explorer"]?.reason
        ?: if (sessionState.capabilities?.fileTransfer == false) "File transfer is not supported by the PC server." else null

    fun load(path: String) {
        currentPath = path
        appContainer.fileExplorerRepository.requestList(path)
    }

    fun refreshDrives() {
        appContainer.fileExplorerRepository.requestDrives()
    }

    fun refreshCurrentDirectory(includeDrives: Boolean = true) {
        if (includeDrives) {
            refreshDrives()
        }
        if (search.isBlank()) {
            load(currentPath)
        } else {
            appContainer.fileExplorerRepository.search(currentPath, search.trim())
        }
    }

    LaunchedEffect(fileTransferAvailable) {
        if (fileTransferAvailable) {
            refreshCurrentDirectory()
        }
    }

    LaunchedEffect(Unit) {
        appContainer.fileExplorerRepository.events.collect { event ->
            when (event) {
                is FileExplorerEvent.DriveListing -> {
                    drives.clear()
                    drives += event.drives.filter { it.isReady }
                    val currentDriveMissing = drives.isNotEmpty() && drives.none { currentPath.startsWith(it.path, ignoreCase = true) }
                    if (currentDriveMissing) {
                        history.clear()
                        history += drives.first().path
                        load(drives.first().path)
                    }
                }
                is FileExplorerEvent.Listing -> {
                    files.clear()
                    files += event.files
                }
                is FileExplorerEvent.FileContent -> {
                    editorState = EditorState(
                        path = event.path,
                        name = event.name,
                        originalContent = event.content,
                        currentContent = event.content,
                    )
                }
                is FileExplorerEvent.Properties -> showingProperties = event.properties
                is FileExplorerEvent.Success -> {
                    snackbars.showSnackbar(event.message)
                    if (editorState == null) {
                        refreshCurrentDirectory()
                    }
                }
                is FileExplorerEvent.Error -> snackbars.showSnackbar(event.message)
            }
        }
    }

    if (editorState != null) {
        FileEditorPage(
            state = editorState!!,
            showLineNumbers = showLineNumbers,
            onToggleLineNumbers = { showLineNumbers = !showLineNumbers },
            onChange = { editorState = editorState?.copy(currentContent = it) },
            onBack = {
                if (editorState?.currentContent != editorState?.originalContent) {
                    confirmDiscard = true
                } else {
                    editorState = null
                    if (fileTransferAvailable) load(currentPath)
                }
            },
            onSave = {
                val state = editorState ?: return@FileEditorPage
                appContainer.fileExplorerRepository.writeFile(state.path, state.currentContent)
                editorState = state.copy(originalContent = state.currentContent)
            },
        )
    } else {
        FileBrowserPage(
            snackbars = snackbars,
            currentPath = currentPath,
            drives = drives,
            files = files,
            search = search,
            canGoUp = history.size > 1,
            hasClipboard = clipboardPath != null,
            enabled = fileTransferAvailable,
            featureReason = fileTransferReason,
            onBack = onBack,
            onSearchChange = { search = it },
            onSearch = {
                if (fileTransferAvailable) {
                    refreshCurrentDirectory(includeDrives = false)
                }
            },
            onClearSearch = {
                search = ""
                if (fileTransferAvailable) {
                    refreshCurrentDirectory(includeDrives = false)
                }
            },
            onReload = {
                if (fileTransferAvailable) {
                    refreshCurrentDirectory()
                }
            },
            onRefreshDrives = { if (fileTransferAvailable) refreshDrives() },
            onUp = {
                if (fileTransferAvailable) {
                    history.removeAt(history.lastIndex)
                    load(history.last())
                }
            },
            onSelectDrive = { drive ->
                if (fileTransferAvailable) {
                    history.clear()
                    history += drive.path
                    load(drive.path)
                }
            },
            onNewFolder = { if (fileTransferAvailable) createType = "folder" },
            onNewFile = { if (fileTransferAvailable) createType = "file" },
            onPaste = {
                if (fileTransferAvailable) {
                    val source = clipboardPath ?: return@FileBrowserPage
                    if (clipboardCut) appContainer.fileExplorerRepository.move(source, currentPath)
                    else appContainer.fileExplorerRepository.copy(source, currentPath)
                    clipboardPath = null
                    clipboardCut = false
                }
            },
            onOpenDirectory = { item ->
                if (fileTransferAvailable) {
                    history += item.path
                    load(item.path)
                }
            },
            onOpenFile = { if (fileTransferAvailable) appContainer.fileExplorerRepository.readFile(it.path) },
            onOpenOnPc = { if (fileTransferAvailable) appContainer.fileExplorerRepository.openFile(it.path) },
            onRename = { if (fileTransferAvailable) renameItem = it },
            onCopy = {
                if (fileTransferAvailable) {
                    clipboardPath = it.path
                    clipboardCut = false
                }
            },
            onCut = {
                if (fileTransferAvailable) {
                    clipboardPath = it.path
                    clipboardCut = true
                }
            },
            onProperties = { if (fileTransferAvailable) appContainer.fileExplorerRepository.properties(it.path) },
            onDelete = { if (fileTransferAvailable) appContainer.fileExplorerRepository.delete(it.path) },
        )
    }

    if (createType != null) {
        NameDialog(
            title = if (createType == "folder") "Create Folder" else "Create File",
            onDismiss = { createType = null },
            onSubmit = { name ->
                if (createType == "folder") appContainer.fileExplorerRepository.createFolder(currentPath, name)
                else appContainer.fileExplorerRepository.createFile(currentPath, name)
                createType = null
            },
        )
    }

    renameItem?.let { item ->
        NameDialog(
            title = "Rename ${item.name}",
            initialValue = item.name,
            onDismiss = { renameItem = null },
            onSubmit = { name ->
                appContainer.fileExplorerRepository.rename(item.path, name)
                renameItem = null
            },
        )
    }

    showingProperties?.let { properties ->
        AlertDialog(
            onDismissRequest = { showingProperties = null },
            title = { Text("Properties") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Name: ${properties.name}")
                    Text("Path: ${properties.path}")
                    Text("Kind: ${properties.kind}")
                    Text("Size: ${properties.size}")
                    Text("Modified: ${properties.modified}")
                    Text("Created: ${properties.created}")
                }
            },
            confirmButton = { OutlinedButton(onClick = { showingProperties = null }) { Text("Close") } },
        )
    }

    if (confirmDiscard) {
        AlertDialog(
            onDismissRequest = { confirmDiscard = false },
            title = { Text("Discard changes?") },
            text = { Text("You have unsaved edits in this file.") },
            confirmButton = {
                TextButton(onClick = {
                    confirmDiscard = false
                    editorState = null
                }) {
                    Text("Discard")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { confirmDiscard = false }) {
                    Text("Keep editing")
                }
            },
        )
    }
}

@Composable
private fun FileBrowserPage(
    snackbars: SnackbarHostState,
    currentPath: String,
    drives: List<DriveInfo>,
    files: List<FileItem>,
    search: String,
    canGoUp: Boolean,
    hasClipboard: Boolean,
    enabled: Boolean,
    featureReason: String?,
    onBack: () -> Unit,
    onSearchChange: (String) -> Unit,
    onSearch: () -> Unit,
    onClearSearch: () -> Unit,
    onReload: () -> Unit,
    onRefreshDrives: () -> Unit,
    onUp: () -> Unit,
    onSelectDrive: (DriveInfo) -> Unit,
    onNewFolder: () -> Unit,
    onNewFile: () -> Unit,
    onPaste: () -> Unit,
    onOpenDirectory: (FileItem) -> Unit,
    onOpenFile: (FileItem) -> Unit,
    onOpenOnPc: (FileItem) -> Unit,
    onRename: (FileItem) -> Unit,
    onCopy: (FileItem) -> Unit,
    onCut: (FileItem) -> Unit,
    onProperties: (FileItem) -> Unit,
    onDelete: (FileItem) -> Unit,
) {
    Scaffold(
        topBar = {
            AppTopBar(
                title = "File Explorer",
                onBack = onBack,
                actions = {
                    if (canGoUp) {
                        IconButton(onClick = onUp) {
                            Icon(Icons.Outlined.UploadFile, contentDescription = "Up")
                        }
                    }
                    IconButton(onClick = onNewFolder) {
                        Icon(Icons.Outlined.CreateNewFolder, contentDescription = "New Folder")
                    }
                    IconButton(onClick = onNewFile) {
                        Icon(Icons.AutoMirrored.Outlined.NoteAdd, contentDescription = "New File")
                    }
                    if (hasClipboard) {
                        IconButton(onClick = onPaste) {
                            Icon(Icons.Outlined.ContentPaste, contentDescription = "Paste")
                        }
                    }
                    IconButton(onClick = onReload) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Refresh")
                    }
                    IconButton(onClick = onRefreshDrives) {
                        Icon(Icons.Outlined.SyncAlt, contentDescription = "Refresh drives")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbars) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (!enabled) {
                Card {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("File Explorer is not ready", style = MaterialTheme.typography.titleMedium)
                        Text(featureReason ?: "The PC server has not enabled file transfer yet.", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            OutlinedTextField(
                value = search,
                onValueChange = onSearchChange,
                label = { Text("Search files") },
                modifier = Modifier.fillMaxWidth(),
                trailingIcon = {
                    Row {
                        TextButton(onClick = onSearch) { Text("Search") }
                        if (search.isNotBlank()) {
                            TextButton(onClick = onClearSearch) { Text("Clear") }
                        }
                    }
                },
            )

            Text(currentPath, style = MaterialTheme.typography.bodyMedium)

            if (drives.isNotEmpty()) {
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    drives.forEach { drive ->
                        OutlinedButton(
                            onClick = { onSelectDrive(drive) },
                            enabled = enabled,
                        ) {
                            Text((drive.label?.takeIf { it.isNotBlank() }?.plus(" • ") ?: "") + drive.path)
                        }
                    }
                }
            }

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(files, key = { it.path }) { item ->
                    FileItemCard(
                        item = item,
                        enabled = enabled,
                        onOpen = { if (item.isDirectory) onOpenDirectory(item) else onOpenFile(item) },
                        onOpenOnPc = { onOpenOnPc(item) },
                        onRename = { onRename(item) },
                        onCopy = { onCopy(item) },
                        onCut = { onCut(item) },
                        onProperties = { onProperties(item) },
                        onDelete = { onDelete(item) },
                    )
                }
            }
        }
    }
}

@Composable
private fun FileItemCard(
    item: FileItem,
    enabled: Boolean,
    onOpen: () -> Unit,
    onOpenOnPc: () -> Unit,
    onRename: () -> Unit,
    onCopy: () -> Unit,
    onCut: () -> Unit,
    onProperties: () -> Unit,
    onDelete: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = enabled, onClick = onOpen),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(fileIcon(item), contentDescription = null, tint = if (item.isDirectory) Color(0xFFF59E0B) else MaterialTheme.colorScheme.primary)
                Column(modifier = Modifier.weight(1f)) {
                    Text(item.name, style = MaterialTheme.typography.titleMedium)
                    Text(
                        if (item.isDirectory) "Directory${item.modified?.let { " • $it" }.orEmpty()}"
                        else "${item.size?.let(::formatSize).orEmpty()}${item.modified?.let { " • $it" }.orEmpty()}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(item.path, style = MaterialTheme.typography.bodySmall)
                }
                if (item.isDirectory) {
                    Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null)
                }
            }
            Row(
                modifier = Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                if (!item.isDirectory) {
                    SmallAction("Open on PC", Icons.AutoMirrored.Outlined.OpenInNew, enabled, onOpenOnPc)
                    SmallAction("Edit", Icons.Outlined.Edit, enabled, onOpen)
                }
                SmallAction("Rename", Icons.Outlined.Edit, enabled, onRename)
                SmallAction("Copy", Icons.Outlined.Description, enabled, onCopy)
                SmallAction("Cut", Icons.Outlined.SyncAlt, enabled, onCut)
                SmallAction("Properties", Icons.Outlined.Info, enabled, onProperties)
                SmallAction("Delete", Icons.Outlined.Delete, enabled, onDelete)
            }
        }
    }
}

@Composable
private fun SmallAction(
    label: String,
    icon: ImageVector,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    TextButton(onClick = onClick, enabled = enabled) {
        Icon(icon, contentDescription = null)
        Text(label, modifier = Modifier.padding(start = 6.dp))
    }
}

@Composable
private fun FileEditorPage(
    state: EditorState,
    showLineNumbers: Boolean,
    onToggleLineNumbers: () -> Unit,
    onChange: (String) -> Unit,
    onBack: () -> Unit,
    onSave: () -> Unit,
) {
    val isDirty = state.currentContent != state.originalContent
    val verticalScroll = rememberScrollState()
    val horizontalScroll = rememberScrollState()

    BackHandler(onBack = onBack)

    Scaffold(
        topBar = {
            AppTopBar(
                title = state.name,
                onBack = onBack,
                actions = {
                    IconButton(onClick = onToggleLineNumbers) {
                        Icon(
                            if (showLineNumbers) Icons.Outlined.Visibility else Icons.Outlined.TextFields,
                            contentDescription = "Toggle line numbers",
                        )
                    }
                    IconButton(onClick = onSave, enabled = isDirty) {
                        Icon(Icons.Outlined.Save, contentDescription = "Save")
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
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (isDirty) {
                    Text(
                        "Modified",
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.labelLarge,
                    )
                }
                Text(state.path, style = MaterialTheme.typography.bodySmall)
            }

            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(18.dp))
                    .padding(12.dp),
            ) {
                if (showLineNumbers) {
                    Text(
                        text = lineNumbers(state.currentContent),
                        modifier = Modifier
                            .width(48.dp)
                            .padding(end = 8.dp)
                            .horizontalScroll(rememberScrollState())
                            .clickable(enabled = false) { }
                            .padding(top = 6.dp),
                        style = TextStyle(
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                        ),
                    )
                }
                BasicTextField(
                    value = state.currentContent,
                    onValueChange = onChange,
                    modifier = Modifier
                        .fillMaxSize()
                        .horizontalScroll(horizontalScroll)
                        .padding(top = 6.dp),
                    textStyle = TextStyle(
                        color = MaterialTheme.colorScheme.onSurface,
                        fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                    ),
                    decorationBox = { inner ->
                        Column(
                            modifier = Modifier
                                .fillMaxSize()
                                .clickable(enabled = false) { }
                                .padding(bottom = 24.dp),
                        ) {
                            inner()
                        }
                    },
                )
            }
        }
    }
}

@Composable
fun NameDialog(
    title: String,
    initialValue: String = "",
    onDismiss: () -> Unit,
    onSubmit: (String) -> Unit,
) {
    var value by remember(initialValue) { mutableStateOf(initialValue) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            OutlinedTextField(value = value, onValueChange = { value = it }, label = { Text("Name") })
        },
        confirmButton = { OutlinedButton(onClick = { if (value.isNotBlank()) onSubmit(value.trim()) }) { Text("Save") } },
        dismissButton = { OutlinedButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

private fun fileIcon(item: FileItem): ImageVector {
    if (item.isDirectory) return Icons.Outlined.Folder
    val ext = item.name.substringAfterLast('.', "").lowercase()
    return when (ext) {
        "txt", "md", "log" -> Icons.Outlined.Description
        "py", "dart", "js", "ts", "java", "cpp", "c", "h", "cs", "kt" -> Icons.Outlined.DataObject
        "json", "xml", "yaml", "yml", "toml" -> Icons.Outlined.DataObject
        "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp" -> Icons.Outlined.Image
        "mp4", "avi", "mkv", "mov", "wmv" -> Icons.Outlined.VideoFile
        "mp3", "wav", "flac", "aac", "ogg" -> Icons.Outlined.AudioFile
        "pdf" -> Icons.Outlined.PictureAsPdf
        "zip", "rar", "7z", "tar", "gz" -> Icons.Outlined.Archive
        else -> Icons.AutoMirrored.Outlined.InsertDriveFile
    }
}

private fun formatSize(bytes: Long): String = when {
    bytes < 1024 -> "$bytes B"
    bytes < 1024 * 1024 -> String.format("%.1f KB", bytes / 1024f)
    bytes < 1024 * 1024 * 1024 -> String.format("%.1f MB", bytes / (1024f * 1024f))
    else -> String.format("%.1f GB", bytes / (1024f * 1024f * 1024f))
}

private fun lineNumbers(text: String): String {
    val count = text.lineSequence().count().coerceAtLeast(1)
    return (1..count).joinToString("\n")
}
