package com.neuralnexusstudios.nexremote.core.feature

import com.neuralnexusstudios.nexremote.core.model.FileItem
import com.neuralnexusstudios.nexremote.core.model.FileProperties
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nexremote.core.network.bool
import com.neuralnexusstudios.nexremote.core.network.string
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull

sealed interface FileExplorerEvent {
    data class Listing(val files: List<FileItem>) : FileExplorerEvent
    data class FileContent(val path: String, val name: String, val content: String) : FileExplorerEvent
    data class Properties(val properties: FileProperties) : FileExplorerEvent
    data class Success(val message: String) : FileExplorerEvent
    data class Error(val message: String) : FileExplorerEvent
}

class FileExplorerRepository(private val connectionRepository: NexRemoteConnectionRepository) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _events = MutableSharedFlow<FileExplorerEvent>(extraBufferCapacity = 32)
    val events: SharedFlow<FileExplorerEvent> = _events

    init {
        scope.launch {
            connectionRepository.messages.collect { payload ->
                if (payload.string("type") == "file_explorer") {
                    when (payload.string("action")) {
                        "list", "search" -> {
                            val files = payload["files"]?.jsonArray?.map { item ->
                                item.jsonObject.let {
                                    FileItem(
                                        name = it.string("name") ?: "Unknown",
                                        path = it.string("path") ?: "",
                                        isDirectory = it.bool("is_directory") ?: false,
                                        size = it["size"]?.jsonPrimitive?.longOrNull,
                                        modified = it.string("modified"),
                                    )
                                }
                            }.orEmpty()
                            _events.tryEmit(FileExplorerEvent.Listing(files))
                        }
                        "file_content" -> _events.tryEmit(
                            FileExplorerEvent.FileContent(
                                path = payload.string("path").orEmpty(),
                                name = payload.string("name").orEmpty(),
                                content = payload.string("content").orEmpty(),
                            ),
                        )
                        "properties" -> _events.tryEmit(
                            FileExplorerEvent.Properties(
                                FileProperties(
                                    name = payload.string("name").orEmpty(),
                                    path = payload.string("path").orEmpty(),
                                    kind = payload.string("kind")
                                        ?: payload.string("item_type")
                                        ?: if (payload.bool("is_directory") == true) "directory" else "file",
                                    size = payload["size"]?.toString().orEmpty(),
                                    modified = payload.string("modified").orEmpty(),
                                    created = payload.string("created").orEmpty(),
                                ),
                            ),
                        )
                        "error" -> _events.tryEmit(FileExplorerEvent.Error(payload.string("message") ?: "An error occurred"))
                        else -> _events.tryEmit(FileExplorerEvent.Success(payload.string("message") ?: "${payload.string("action").orEmpty().replace('_', ' ')} completed"))
                    }
                }
            }
        }
    }

    fun requestList(path: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "list", "path" to path))
    fun search(path: String, query: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "search", "path" to path, "query" to query))
    fun openFile(path: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "open", "path" to path))
    fun readFile(path: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "read_file", "path" to path))
    fun writeFile(path: String, content: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "write_file", "path" to path, "content" to content))
    fun createFolder(path: String, name: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "create_folder", "path" to path, "name" to name))
    fun createFile(path: String, name: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "create_file", "path" to path, "name" to name, "content" to ""))
    fun rename(path: String, newName: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "rename", "path" to path, "new_name" to newName))
    fun delete(path: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "delete", "path" to path))
    fun copy(source: String, destination: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "copy", "source" to source, "destination" to destination))
    fun move(source: String, destination: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "move", "source" to source, "destination" to destination))
    fun properties(path: String) = connectionRepository.sendMessage(mapOf("type" to "file_explorer", "action" to "properties", "path" to path))
}
