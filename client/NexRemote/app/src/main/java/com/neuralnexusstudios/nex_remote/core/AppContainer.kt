package com.neuralnexusstudios.nex_remote.core

import android.content.Context
import com.neuralnexusstudios.nex_remote.core.feature.CameraRepository
import com.neuralnexusstudios.nex_remote.core.feature.FileExplorerRepository
import com.neuralnexusstudios.nex_remote.core.feature.GamepadRepository
import com.neuralnexusstudios.nex_remote.core.feature.MediaRepository
import com.neuralnexusstudios.nex_remote.core.feature.ScreenShareRepository
import com.neuralnexusstudios.nex_remote.core.feature.TaskManagerRepository
import com.neuralnexusstudios.nex_remote.core.network.DiscoveryRepository
import com.neuralnexusstudios.nex_remote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nex_remote.core.storage.AppPreferences
import com.neuralnexusstudios.nex_remote.core.storage.CertificateStore
import com.neuralnexusstudios.nex_remote.core.storage.ClientIdentityStore

class AppContainer(context: Context) {
    private val appContext = context.applicationContext

    val preferences = AppPreferences(appContext)
    val certificateStore = CertificateStore(appContext)
    val clientIdentityStore = ClientIdentityStore(appContext)
    val connectionRepository = NexRemoteConnectionRepository(
        context = appContext,
        preferences = preferences,
        certificateStore = certificateStore,
        clientIdentityStore = clientIdentityStore,
    )
    val discoveryRepository = DiscoveryRepository(appContext)
    val mediaRepository = MediaRepository(connectionRepository)
    val screenShareRepository = ScreenShareRepository(connectionRepository)
    val cameraRepository = CameraRepository(connectionRepository)
    val fileExplorerRepository = FileExplorerRepository(connectionRepository)
    val taskManagerRepository = TaskManagerRepository(connectionRepository)
    val gamepadRepository = GamepadRepository(
        preferences = preferences,
        connectionRepository = connectionRepository,
    )
}
