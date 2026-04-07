package com.neuralnexusstudios.nexremote.core.feature

import com.neuralnexusstudios.nexremote.core.model.ProcessInfo
import com.neuralnexusstudios.nexremote.core.model.SystemInfo
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nexremote.core.network.double
import com.neuralnexusstudios.nexremote.core.network.int
import com.neuralnexusstudios.nexremote.core.network.string
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull

enum class TaskProcessSortKey { Name, Pid, Cpu, Memory }

class TaskManagerRepository(private val connectionRepository: NexRemoteConnectionRepository) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _processMap = MutableStateFlow<Map<Int, ProcessInfo>>(emptyMap())
    private val _processOrder = MutableStateFlow<List<Int>>(emptyList())
    private val _searchQuery = MutableStateFlow("")
    private val _sortKey = MutableStateFlow(TaskProcessSortKey.Cpu)
    private val _ascending = MutableStateFlow(false)
    private val _systemInfo = MutableStateFlow(SystemInfo())
    private val _messages = MutableSharedFlow<String>(extraBufferCapacity = 8)

    val processMap: StateFlow<Map<Int, ProcessInfo>> = _processMap
    val searchQuery: StateFlow<String> = _searchQuery
    val sortKey: StateFlow<TaskProcessSortKey> = _sortKey
    val ascending: StateFlow<Boolean> = _ascending
    val systemInfo: StateFlow<SystemInfo> = _systemInfo
    val messages: SharedFlow<String> = _messages
    @OptIn(FlowPreview::class)
    val visibleProcessIds: StateFlow<List<Int>> = combine(
        _processMap,
        _processOrder,
        _searchQuery.debounce(180),
        _sortKey,
        _ascending,
    ) { processMap, processOrder, search, sortKey, ascending ->
        val normalizedSearch = search.trim()
        val baseIds = if (normalizedSearch.isBlank()) {
            processOrder
        } else {
            processOrder.filter { pid ->
                processMap[pid]?.name?.contains(normalizedSearch, ignoreCase = true) == true
            }
        }

        if (sortKey == TaskProcessSortKey.Cpu && !ascending && normalizedSearch.isBlank()) {
            baseIds
        } else {
            baseIds.sortedWith(processComparator(processMap, sortKey, ascending))
        }
    }.stateIn(scope, SharingStarted.WhileSubscribed(5_000), emptyList())

    init {
        scope.launch {
            connectionRepository.messages.collect { payload ->
                if (payload.string("type") == "task_manager") {
                    when (payload.string("action")) {
                        "snapshot" -> {
                            payload["system"]?.jsonObject?.let { system ->
                                _systemInfo.value = SystemInfo(
                                    cpuUsage = system.double("cpu_usage") ?: 0.0,
                                    memoryUsage = system.double("memory_usage") ?: 0.0,
                                    diskUsage = system.double("disk_usage") ?: 0.0,
                                )
                            }
                            applyProcessSnapshot(payload["processes"]?.jsonArray)
                        }
                        "list_processes" -> applyProcessSnapshot(payload["processes"]?.jsonArray)
                        "system_info" -> {
                            _systemInfo.value = SystemInfo(
                                cpuUsage = payload.double("cpu_usage") ?: 0.0,
                                memoryUsage = payload.double("memory_usage") ?: 0.0,
                                diskUsage = payload.double("disk_usage") ?: 0.0,
                            )
                        }
                        "error" -> _messages.tryEmit(payload.string("message") ?: "Task Manager error")
                        "process_ended" -> _messages.tryEmit("Process terminated successfully")
                    }
                }
            }
        }
    }

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun updateSort(requested: TaskProcessSortKey) {
        val current = _sortKey.value
        val nextAscending = if (requested == current) {
            !_ascending.value
        } else {
            requested == TaskProcessSortKey.Name || requested == TaskProcessSortKey.Pid
        }

        _sortKey.value = requested
        _ascending.value = nextAscending
    }

    fun processFor(pid: Int): ProcessInfo? = _processMap.value[pid]

    fun requestSnapshot() = connectionRepository.sendMessage(mapOf("type" to "task_manager", "action" to "snapshot"))
    fun requestProcesses() = connectionRepository.sendMessage(mapOf("type" to "task_manager", "action" to "list_processes"))
    fun requestSystemInfo() = connectionRepository.sendMessage(mapOf("type" to "task_manager", "action" to "system_info"))
    fun endProcess(pid: Int) = connectionRepository.sendMessage(mapOf("type" to "task_manager", "action" to "end_process", "pid" to pid))

    private fun applyProcessSnapshot(processArray: kotlinx.serialization.json.JsonArray?) {
        val currentMap = _processMap.value
        val nextMap = LinkedHashMap<Int, ProcessInfo>(processArray?.size ?: 0)
        val nextOrder = ArrayList<Int>(processArray?.size ?: 0)

        processArray?.forEach { item ->
            val process = item.jsonObject.let {
                ProcessInfo(
                    name = it.string("name") ?: "Unknown",
                    pid = it.int("pid") ?: 0,
                    cpu = it.double("cpu") ?: 0.0,
                    memory = it["memory"]?.jsonPrimitive?.longOrNull ?: 0L,
                )
            }

            val reused = currentMap[process.pid]?.takeIf { it == process } ?: process
            nextMap[process.pid] = reused
            nextOrder += process.pid
        }

        _processMap.value = nextMap
        _processOrder.value = nextOrder
    }

    private fun processComparator(
        processMap: Map<Int, ProcessInfo>,
        sortKey: TaskProcessSortKey,
        ascending: Boolean,
    ): Comparator<Int> {
        val comparator = when (sortKey) {
            TaskProcessSortKey.Name -> compareBy<Int> { processMap[it]?.name?.lowercase() ?: "" }
            TaskProcessSortKey.Pid -> compareBy<Int> { processMap[it]?.pid ?: 0 }
            TaskProcessSortKey.Cpu -> compareBy<Int> { processMap[it]?.cpu ?: 0.0 }
            TaskProcessSortKey.Memory -> compareBy<Int> { processMap[it]?.memory ?: 0L }
        }

        return if (ascending) comparator else comparator.reversed()
    }
}
