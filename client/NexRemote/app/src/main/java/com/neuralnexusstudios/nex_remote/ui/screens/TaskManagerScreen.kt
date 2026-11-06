package com.neuralnexusstudios.nex_remote.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material.icons.outlined.Search
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.composables.ui.components.Text
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.core.feature.TaskManagerRepository
import com.neuralnexusstudios.nex_remote.core.feature.TaskProcessSortKey
import com.neuralnexusstudios.nex_remote.core.model.ProcessInfo
import com.neuralnexusstudios.nex_remote.core.model.SystemInfo
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxCard
import com.neuralnexusstudios.nex_remote.ui.design.NxChip
import com.neuralnexusstudios.nex_remote.ui.design.NxIconButton
import com.neuralnexusstudios.nex_remote.ui.design.NxScaffold
import com.neuralnexusstudios.nex_remote.ui.design.NxTextField
import com.neuralnexusstudios.nex_remote.ui.design.NxTone
import com.neuralnexusstudios.nex_remote.ui.design.NxType
import com.neuralnexusstudios.nex_remote.ui.design.rememberNxSnackbarState
import com.patrykandpatrick.vico.compose.cartesian.CartesianChartHost
import com.patrykandpatrick.vico.compose.cartesian.axis.VerticalAxis
import com.patrykandpatrick.vico.compose.cartesian.axis.rememberAxisGuidelineComponent
import com.patrykandpatrick.vico.compose.cartesian.axis.rememberAxisLabelComponent
import com.patrykandpatrick.vico.compose.cartesian.data.CartesianChartModelProducer
import com.patrykandpatrick.vico.compose.cartesian.data.CartesianLayerRangeProvider
import com.patrykandpatrick.vico.compose.cartesian.data.CartesianValueFormatter
import com.patrykandpatrick.vico.compose.cartesian.data.lineSeries
import com.patrykandpatrick.vico.compose.cartesian.layer.LineCartesianLayer
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberLine
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberLineCartesianLayer
import com.patrykandpatrick.vico.compose.cartesian.rememberCartesianChart
import com.patrykandpatrick.vico.compose.cartesian.rememberVicoScrollState
import com.patrykandpatrick.vico.compose.common.Fill
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Locale

private const val POLL_MS = 1_000L
private val CpuColor = Color(0xFFE5202E)
private val MemColor = Color(0xFF3DDC84)
private val DiskColor = Color(0xFFFFB547)

@Composable
fun TaskManagerScreen(
    appContainer: AppContainer,
    onBack: () -> Unit,
) {
    val repo = appContainer.taskManagerRepository
    val scope = rememberCoroutineScope()
    val snackbars = rememberNxSnackbarState()
    val processMap by repo.processMap.collectAsState()
    val visibleProcessIds by repo.visibleProcessIds.collectAsState()
    val systemInfo by repo.systemInfo.collectAsState()
    val history by repo.history.collectAsState()
    val search by repo.searchQuery.collectAsState()
    val sortKey by repo.sortKey.collectAsState()
    val ascending by repo.ascending.collectAsState()
    val sessionState by appContainer.connectionRepository.serverSessionState.collectAsState()
    var showChart by rememberSaveable { mutableStateOf(true) }
    val available = sessionState.connected && sessionState.featureStatus["task_manager"]?.available != false
    val reason = sessionState.featureStatus["task_manager"]?.reason

    LaunchedEffect(Unit) {
        launch {
            while (true) {
                val state = appContainer.connectionRepository.serverSessionState.value
                if (state.connected && state.featureStatus["task_manager"]?.available != false) repo.requestSnapshot()
                delay(POLL_MS)
            }
        }
        launch { repo.messages.collect { snackbars.showSnackbar(it) } }
    }

    NxScaffold(
        title = "Task Manager",
        onBack = onBack,
        snackbar = snackbars,
        actions = {
            NxIconButton(
                Icons.Outlined.ShowChart,
                contentDescription = if (showChart) "Hide chart" else "Show chart",
                onClick = { showChart = !showChart },
                tint = if (showChart) Nx.primary else Nx.muted,
            )
        },
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (!available) {
                item {
                    NxCard(Modifier.fillMaxWidth(), tone = NxTone.Warning) {
                        Text("Task Manager is not ready", style = NxType.titleSmall)
                        Text(reason ?: "Connect to your PC first.", style = NxType.bodySmall, color = Nx.muted)
                    }
                }
            }
            item { StatTiles(systemInfo) }
            if (showChart) item { UsageChart(history) }
            item {
                NxTextField(
                    value = search,
                    onValueChange = repo::updateSearchQuery,
                    placeholder = "Search processes",
                    leadingIcon = Icons.Outlined.Search,
                    modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                )
            }
            item {
                ProcessHeader(sortKey, ascending, repo::updateSort, systemInfo.processCount ?: processMap.size)
            }
            items(visibleProcessIds, key = { it }) { pid ->
                val process = processMap[pid] ?: return@items
                ProcessRow(
                    process = process,
                    memoryTotal = systemInfo.memoryTotal,
                    enabled = available,
                    onEnd = {
                        if (available) repo.endProcess(process.pid)
                        else scope.launch { snackbars.showSnackbar(reason ?: "Task Manager is not ready yet.") }
                    },
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------------- tiles

@Composable
private fun StatTiles(info: SystemInfo) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        StatTile("CPU", "${"%.0f".format(info.cpuUsage)}%", info.cpuUsage / 100.0, CpuColor, Modifier.weight(1f))
        StatTile("Memory", "${"%.0f".format(info.memoryUsage)}%", info.memoryUsage / 100.0, MemColor, Modifier.weight(1f))
        // Disk activity on 1.2+ hosts (like Windows Task Manager); space used on older hosts.
        val disk = info.diskActive ?: info.diskUsage
        StatTile(if (info.diskActive != null) "Disk" else "Disk used", "${"%.0f".format(disk)}%", disk / 100.0, DiskColor, Modifier.weight(1f))
    }
    if (info.netRecvBps != null || info.netSentBps != null) {
        Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NetTile("Download", formatRate(info.netRecvBps ?: 0.0), Modifier.weight(1f))
            NetTile("Upload", formatRate(info.netSentBps ?: 0.0), Modifier.weight(1f))
        }
    }
}

@Composable
private fun StatTile(label: String, value: String, fraction: Double, color: Color, modifier: Modifier) {
    NxCard(modifier, contentPadding = PaddingValues(14.dp)) {
        Text(label, style = NxType.label, color = Nx.muted)
        Text(value, style = NxType.headline, color = if (fraction > 0.85) Nx.danger else Nx.onPanel)
        Box(Modifier.fillMaxWidth().height(4.dp).clip(CircleShape).background(Nx.panelRaised)) {
            Box(Modifier.fillMaxWidth(fraction.toFloat().coerceIn(0f, 1f)).height(4.dp).clip(CircleShape).background(color))
        }
    }
}

@Composable
private fun NetTile(label: String, value: String, modifier: Modifier) {
    NxCard(modifier, tone = NxTone.Raised, contentPadding = PaddingValues(horizontal = 14.dp, vertical = 10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(label, style = NxType.label, color = Nx.muted, modifier = Modifier.weight(1f))
            Text(value, style = NxType.titleSmall)
        }
    }
}

// ---------------------------------------------------------------------------------- chart

/**
 * Live usage chart (Vico). The x range is fixed to the last [TaskManagerRepository.HISTORY_SIZE]
 * samples and new samples are placed at the right edge, so the lines enter from the right and scroll
 * left (like Windows Task Manager) instead of growing from the left.
 */
@Composable
private fun UsageChart(history: List<SystemInfo>) {
    val window = TaskManagerRepository.HISTORY_SIZE
    val modelProducer = remember { CartesianChartModelProducer() }
    LaunchedEffect(history) {
        if (history.isEmpty()) return@LaunchedEffect
        val firstX = window - history.size
        val xs = history.indices.map { firstX + it }
        modelProducer.runTransaction {
            lineSeries {
                series(xs, history.map { it.cpuUsage.coerceIn(0.0, 100.0) })
                series(xs, history.map { it.memoryUsage.coerceIn(0.0, 100.0) })
                series(xs, history.map { (it.diskActive ?: it.diskUsage).coerceIn(0.0, 100.0) })
            }
        }
    }

    NxCard(Modifier.fillMaxWidth(), contentPadding = PaddingValues(start = 8.dp, end = 14.dp, top = 14.dp, bottom = 10.dp)) {
        Row(Modifier.padding(start = 8.dp), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("Last minute", style = NxType.titleSmall, modifier = Modifier.weight(1f))
            Legend("CPU", CpuColor)
            Legend("Memory", MemColor)
            Legend("Disk", DiskColor)
        }
        val lines = listOf(CpuColor, MemColor, DiskColor).map { color ->
            LineCartesianLayer.rememberLine(
                fill = remember(color) { LineCartesianLayer.LineFill.single(Fill(color)) },
                areaFill = if (color == CpuColor) {
                    remember(color) {
                        LineCartesianLayer.AreaFill.single(Fill(Brush.verticalGradient(listOf(color.copy(alpha = 0.35f), Color.Transparent))))
                    }
                } else {
                    null
                },
                interpolator = remember { LineCartesianLayer.Interpolator.cubic() },
            )
        }
        val labelColor = Nx.muted
        val guideColor = Nx.border
        CartesianChartHost(
            chart = rememberCartesianChart(
                rememberLineCartesianLayer(
                    lineProvider = LineCartesianLayer.LineProvider.series(lines),
                    rangeProvider = remember { CartesianLayerRangeProvider.fixed(minX = 0.0, maxX = (window - 1).toDouble(), minY = 0.0, maxY = 100.0) },
                ),
                startAxis = VerticalAxis.rememberStart(
                    label = rememberAxisLabelComponent(style = NxType.label.copy(color = labelColor)),
                    guideline = rememberAxisGuidelineComponent(fill = Fill(guideColor)),
                    line = null,
                    tick = null,
                    itemPlacer = remember { VerticalAxis.ItemPlacer.step({ 25.0 }) },
                    valueFormatter = remember { CartesianValueFormatter { _, value, _ -> "${value.toInt()}%" } },
                ),
            ),
            modelProducer = modelProducer,
            modifier = Modifier.fillMaxWidth().height(170.dp),
            scrollState = rememberVicoScrollState(scrollEnabled = false),
            animationSpec = null, // a new sample every second; tweening between shifts looks jittery
        )
    }
}

@Composable
private fun Legend(label: String, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(color))
        Text(label, style = NxType.label, color = Nx.muted)
    }
}

// ---------------------------------------------------------------------------------- processes

@Composable
private fun ProcessHeader(sortKey: TaskProcessSortKey, ascending: Boolean, onSort: (TaskProcessSortKey) -> Unit, count: Int) {
    Column(Modifier.fillMaxWidth().padding(top = 4.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("$count processes", style = NxType.label, color = Nx.muted, modifier = Modifier.weight(1f))
            listOf(TaskProcessSortKey.Cpu to "CPU", TaskProcessSortKey.Memory to "Memory", TaskProcessSortKey.Name to "Name").forEach { (key, label) ->
                NxChip(
                    label = if (sortKey == key) "$label ${if (ascending) "↑" else "↓"}" else label,
                    selected = sortKey == key,
                    onClick = { onSort(key) },
                )
            }
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp)) {
            HeaderCell("Name", 0.5f) { onSort(TaskProcessSortKey.Name) }
            HeaderCell("CPU", 0.18f) { onSort(TaskProcessSortKey.Cpu) }
            HeaderCell("Memory", 0.2f) { onSort(TaskProcessSortKey.Memory) }
            Box(Modifier.weight(0.12f))
        }
    }
}

@Composable
private fun RowScope.HeaderCell(label: String, weight: Float, onClick: () -> Unit) {
    Text(label, style = NxType.overline, color = Nx.muted, modifier = Modifier.weight(weight).clickable(onClick = onClick))
}

@Composable
private fun ProcessRow(process: ProcessInfo, memoryTotal: Long?, enabled: Boolean, onEnd: () -> Unit) {
    val shape = RoundedCornerShape(14.dp)
    Row(
        Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(Nx.panel)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(0.5f)) {
            Text(process.name, style = NxType.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("PID ${process.pid}", style = NxType.bodySmall, color = Nx.muted)
        }
        Column(Modifier.weight(0.18f)) {
            Text("${"%.1f".format(process.cpu)}%", style = NxType.label, color = cpuColor(process.cpu))
            UsageBar(process.cpu / 100.0, CpuColor)
        }
        Column(Modifier.weight(0.2f).padding(start = 6.dp)) {
            Text(formatBytes(process.memory), style = NxType.label)
            if (memoryTotal != null && memoryTotal > 0) UsageBar(process.memory.toDouble() / memoryTotal, MemColor)
        }
        Box(Modifier.weight(0.12f), contentAlignment = Alignment.CenterEnd) {
            NxChip(label = "End", selected = false, onClick = onEnd, enabled = enabled)
        }
    }
}

@Composable
private fun UsageBar(fraction: Double, color: Color) {
    Box(Modifier.padding(top = 4.dp, end = 8.dp).fillMaxWidth().height(3.dp).clip(CircleShape).background(Nx.panelRaised)) {
        Box(Modifier.fillMaxWidth(fraction.toFloat().coerceIn(0.02f, 1f)).height(3.dp).clip(CircleShape).background(color))
    }
}

@Composable
private fun cpuColor(cpu: Double): Color = when {
    cpu >= 50 -> Nx.danger
    cpu >= 15 -> Nx.warning
    else -> Nx.onPanel
}

private fun formatBytes(bytes: Long): String = when {
    bytes < 1024 -> "$bytes B"
    bytes < 1024 * 1024 -> "${bytes / 1024} KB"
    bytes < 1024L * 1024 * 1024 -> String.format(Locale.ROOT, "%.0f MB", bytes / (1024.0 * 1024.0))
    else -> String.format(Locale.ROOT, "%.1f GB", bytes / (1024.0 * 1024.0 * 1024.0))
}

private fun formatRate(bytesPerSecond: Double): String {
    val bits = bytesPerSecond * 8
    return when {
        bits < 1_000 -> String.format(Locale.ROOT, "%.0f bps", bits)
        bits < 1_000_000 -> String.format(Locale.ROOT, "%.0f Kbps", bits / 1_000)
        bits < 1_000_000_000 -> String.format(Locale.ROOT, "%.1f Mbps", bits / 1_000_000)
        else -> String.format(Locale.ROOT, "%.2f Gbps", bits / 1_000_000_000)
    }
}
