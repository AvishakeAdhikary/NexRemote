package com.neuralnexusstudios.nexremote.core.feature

import com.neuralnexusstudios.nexremote.core.model.ProcessInfo
import com.neuralnexusstudios.nexremote.core.model.SystemInfo
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nexremote.core.network.double
import com.neuralnexusstudios.nexremote.core.network.int
import com.neuralnexusstudios.nexremote.core.network.string
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull

class TaskManagerRepository(private val connectionRepository: NexRemoteConnectionRepository) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _processes = MutableStateFlow<List<ProcessInfo>>(emptyList())
    private val _systemInfo = MutableStateFlow(SystemInfo())
    private val _messages = MutableSharedFlow<String>(extraBufferCapacity = 8)

    val processes: StateFlow<List<ProcessInfo>> = _processes
    val systemInfo: StateFlow<SystemInfo> = _systemInfo
    val messages: SharedFlow<String> = _messages

    init {
        scope.launch {
            connectionRepository.messages.collect { payload ->
                if (payload.string("type") == "task_manager") {
                    when (payload.string("action")) {
                        "list_processes" -> {
                            _processes.value = payload["processes"]?.jsonArray?.map { item ->
                                item.jsonObject.let {
                                    ProcessInfo(
                                        name = it.string("name") ?: "Unknown",
                                        pid = it.int("pid") ?: 0,
                                        cpu = it.double("cpu") ?: 0.0,
                                        memory = it["memory"]?.jsonPrimitive?.longOrNull ?: 0L,
                                    )
                                }
                            }.orEmpty()
                        }
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

    fun requestProcesses() = connectionRepository.sendMessage(mapOf("type" to "task_manager", "action" to "list_processes"))
    fun requestSystemInfo() = connectionRepository.sendMessage(mapOf("type" to "task_manager", "action" to "system_info"))
    fun endProcess(pid: Int) = connectionRepository.sendMessage(mapOf("type" to "task_manager", "action" to "end_process", "pid" to pid))
}
