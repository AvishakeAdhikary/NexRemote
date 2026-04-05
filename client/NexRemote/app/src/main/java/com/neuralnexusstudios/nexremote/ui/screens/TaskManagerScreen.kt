package com.neuralnexusstudios.nexremote.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding

import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.BarChart
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.core.model.ProcessInfo
import com.neuralnexusstudios.nexremote.core.model.SystemInfo
import com.neuralnexusstudios.nexremote.ui.components.AppTopBar
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private enum class ProcessSortKey { Name, Pid, Cpu, Memory }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TaskManagerScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val snackbars = remember { SnackbarHostState() }
    val processes by appContainer.taskManagerRepository.processes.collectAsState()
    val systemInfo by appContainer.taskManagerRepository.systemInfo.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    val history = remember { mutableStateListOf<SystemInfo>() }
    var search by remember { mutableStateOf("") }
    var sortKey by remember { mutableStateOf(ProcessSortKey.Cpu) }
    var ascending by remember { mutableStateOf(false) }
    var showGraphs by remember { mutableStateOf(true) }
    val taskManagerAvailable = sessionState.connected && sessionState.featureStatus["task_manager"]?.available != false
    val taskManagerReason = sessionState.featureStatus["task_manager"]?.reason

    LaunchedEffect(Unit) {
        launch {
            while (true) {
                val ready = appContainer.connectionRepository.serverSessionState.value.connected &&
                    appContainer.connectionRepository.serverSessionState.value.featureStatus["task_manager"]?.available != false
                if (ready) {
                    appContainer.taskManagerRepository.requestProcesses()
                    appContainer.taskManagerRepository.requestSystemInfo()
                }
                delay(2_000)
            }
        }
        launch {
            appContainer.taskManagerRepository.messages.collect { snackbars.showSnackbar(it) }
        }
    }

    LaunchedEffect(systemInfo) {
        if (history.isEmpty() || history.last() != systemInfo) {
            history += systemInfo
            while (history.size > 30) {
                history.removeAt(0)
            }
        }
    }

    val filtered = processes
        .filter { it.name.contains(search, ignoreCase = true) }
        .sortedWith(
            compareBy<ProcessInfo> {
                when (sortKey) {
                    ProcessSortKey.Name -> it.name.lowercase()
                    ProcessSortKey.Pid -> it.pid
                    ProcessSortKey.Cpu -> it.cpu
                    ProcessSortKey.Memory -> it.memory
                }
            }.let { comparator ->
                if (ascending) comparator else comparator.reversed()
            },
        )

    Scaffold(
        topBar = {
            AppTopBar(
                title = "Task Manager",
                onBack = onBack,
                actions = {
                    IconButton(onClick = { showGraphs = !showGraphs }) {
                        Icon(Icons.Outlined.BarChart, contentDescription = "Toggle graphs")
                    }
                    IconButton(onClick = {
                        if (taskManagerAvailable) {
                            appContainer.taskManagerRepository.requestProcesses()
                            appContainer.taskManagerRepository.requestSystemInfo()
                        } else {
                            scope.launch { snackbars.showSnackbar(taskManagerReason ?: "Task Manager is not ready yet.") }
                        }
                    }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Refresh")
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
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (!taskManagerAvailable) {
                Card {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Task Manager is not ready", style = MaterialTheme.typography.titleMedium)
                        Text(taskManagerReason ?: "The PC server has not enabled process telemetry yet.", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            SystemSummaryCard(systemInfo = systemInfo)

            if (showGraphs) {
                ResourceHistoryCard(history = history)
            }

            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                label = { Text("Search processes") },
                modifier = Modifier.fillMaxWidth(),
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                SortChip("Name", sortKey == ProcessSortKey.Name) { updateSort(ProcessSortKey.Name, sortKey, ascending) { sortKey = it.first; ascending = it.second } }
                SortChip("PID", sortKey == ProcessSortKey.Pid) { updateSort(ProcessSortKey.Pid, sortKey, ascending) { sortKey = it.first; ascending = it.second } }
                SortChip("CPU", sortKey == ProcessSortKey.Cpu) { updateSort(ProcessSortKey.Cpu, sortKey, ascending) { sortKey = it.first; ascending = it.second } }
                SortChip("Memory", sortKey == ProcessSortKey.Memory) { updateSort(ProcessSortKey.Memory, sortKey, ascending) { sortKey = it.first; ascending = it.second } }
            }

            ProcessTableHeader(
                sortKey = sortKey,
                ascending = ascending,
                onSort = { key -> updateSort(key, sortKey, ascending) { sortKey = it.first; ascending = it.second } },
            )

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(filtered, key = { it.pid }) { process ->
                    ProcessRow(
                        process = process,
                        onEnd = {
                            if (taskManagerAvailable) {
                                appContainer.taskManagerRepository.endProcess(process.pid)
                            } else {
                                scope.launch { snackbars.showSnackbar(taskManagerReason ?: "Task Manager is not ready yet.") }
                            }
                        },
                        enabled = taskManagerAvailable,
                    )
                }
            }
        }
    }
}

@Composable
private fun SystemSummaryCard(systemInfo: SystemInfo) {
    Card {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            SummaryPill("CPU", systemInfo.cpuUsage, Color(0xFF3B82F6))
            SummaryPill("RAM", systemInfo.memoryUsage, Color(0xFF10B981))
            SummaryPill("Disk", systemInfo.diskUsage, Color(0xFFF59E0B))
        }
    }
}

@Composable
private fun SummaryPill(label: String, value: Double, color: Color) {
    Column(horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
        Text(label, style = MaterialTheme.typography.labelMedium)
        Text(
            "${"%.1f".format(value)}%",
            color = if (value > 80) MaterialTheme.colorScheme.error else color,
            style = MaterialTheme.typography.titleMedium,
        )
    }
}

@Composable
private fun ResourceHistoryCard(history: List<SystemInfo>) {
    Card {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Live usage", style = MaterialTheme.typography.titleMedium)
            ResourceLegend("CPU", Color(0xFF3B82F6))
            ResourceLegend("RAM", Color(0xFF10B981))
            ResourceLegend("Disk", Color(0xFFF59E0B))
            MiniGraph(
                series = listOf(
                    history.map { it.cpuUsage.toFloat() } to Color(0xFF3B82F6),
                    history.map { it.memoryUsage.toFloat() } to Color(0xFF10B981),
                    history.map { it.diskUsage.toFloat() } to Color(0xFFF59E0B),
                ),
            )
        }
    }
}

@Composable
private fun ResourceLegend(label: String, color: Color) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(
            modifier = Modifier
                .padding(top = 4.dp)
                .height(10.dp)
                .fillMaxWidth(0.05f)
                .background(color, RoundedCornerShape(50)),
        )
        Text(label, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun MiniGraph(series: List<Pair<List<Float>, Color>>) {
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(140.dp),
    ) {
        drawLine(Color(0x33222222), Offset(0f, size.height), Offset(size.width, size.height), strokeWidth = 2f)
        drawLine(Color(0x33222222), Offset(0f, size.height / 2f), Offset(size.width, size.height / 2f), strokeWidth = 1f)
        drawLine(Color(0x33222222), Offset(0f, 0f), Offset(size.width, 0f), strokeWidth = 1f)

        series.forEach { (points, color) ->
            if (points.size < 2) return@forEach
            val step = size.width / (points.lastIndex.coerceAtLeast(1))
            val path = Path().apply {
                points.forEachIndexed { index, value ->
                    val x = index * step
                    val y = size.height - (value.coerceIn(0f, 100f) / 100f * size.height)
                    if (index == 0) moveTo(x, y) else lineTo(x, y)
                }
            }
            drawPath(
                path = path,
                color = color,
                style = Stroke(width = 4f, cap = StrokeCap.Round),
            )
        }
    }
}

@Composable
private fun SortChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    FilterChip(selected = selected, onClick = onClick, label = { Text(label) })
}

@Composable
private fun ProcessTableHeader(
    sortKey: ProcessSortKey,
    ascending: Boolean,
    onSort: (ProcessSortKey) -> Unit,
) {
    Card {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            HeaderCell("Process", 0.42f, sortKey == ProcessSortKey.Name, ascending) { onSort(ProcessSortKey.Name) }
            HeaderCell("PID", 0.14f, sortKey == ProcessSortKey.Pid, ascending) { onSort(ProcessSortKey.Pid) }
            HeaderCell("CPU", 0.18f, sortKey == ProcessSortKey.Cpu, ascending) { onSort(ProcessSortKey.Cpu) }
            HeaderCell("RAM", 0.18f, sortKey == ProcessSortKey.Memory, ascending) { onSort(ProcessSortKey.Memory) }
            Text("Action", modifier = Modifier.weight(0.18f), style = MaterialTheme.typography.labelLarge)
        }
    }
}

@Composable
private fun RowScope.HeaderCell(
    label: String,
    weight: Float,
    active: Boolean,
    ascending: Boolean,
    onClick: () -> Unit,
) {
    Text(
        text = if (active) "$label ${if (ascending) "↑" else "↓"}" else label,
        modifier = Modifier
            .weight(weight)
            .clickable(onClick = onClick),
        style = MaterialTheme.typography.labelLarge,
    )
}

@Composable
private fun ProcessRow(
    process: ProcessInfo,
    onEnd: () -> Unit,
    enabled: Boolean = true,
) {
    Card {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Column(modifier = Modifier.weight(0.42f)) {
                Text(process.name, style = MaterialTheme.typography.titleSmall)
                Text(
                    if (process.cpu > 50) "High activity" else "Normal activity",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (process.cpu > 50) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(process.pid.toString(), modifier = Modifier.weight(0.14f))
            Text("${"%.1f".format(process.cpu)}%", modifier = Modifier.weight(0.18f), color = cpuColor(process.cpu))
            Text(formatBytes(process.memory), modifier = Modifier.weight(0.18f))
            TextButton(onClick = onEnd, modifier = Modifier.weight(0.18f), enabled = enabled) {
                Text("End")
            }
        }
    }
}

private fun updateSort(
    requested: ProcessSortKey,
    current: ProcessSortKey,
    ascending: Boolean,
    apply: (Pair<ProcessSortKey, Boolean>) -> Unit,
) {
    val nextAscending = if (requested == current) !ascending else requested == ProcessSortKey.Name || requested == ProcessSortKey.Pid
    apply(requested to nextAscending)
}

private fun cpuColor(cpu: Double): Color = when {
    cpu >= 70 -> Color(0xFFDC2626)
    cpu >= 35 -> Color(0xFFF59E0B)
    else -> Color(0xFF10B981)
}

private fun formatBytes(bytes: Long): String = when {
    bytes < 1024 -> "$bytes B"
    bytes < 1024 * 1024 -> "${bytes / 1024} KB"
    bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
    else -> String.format("%.1f GB", bytes / (1024f * 1024f * 1024f))
}
