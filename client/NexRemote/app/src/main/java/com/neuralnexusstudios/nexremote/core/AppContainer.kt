package com.neuralnexusstudios.nexremote.core

import android.content.Context
import com.neuralnexusstudios.nexremote.core.feature.CameraRepository
import com.neuralnexusstudios.nexremote.core.feature.FileExplorerRepository
import com.neuralnexusstudios.nexremote.core.feature.GamepadRepository
import com.neuralnexusstudios.nexremote.core.feature.MediaRepository
import com.neuralnexusstudios.nexremote.core.feature.ScreenShareRepository
import com.neuralnexusstudios.nexremote.core.feature.TaskManagerRepository
import com.neuralnexusstudios.nexremote.core.network.DiscoveryRepository
import com.neuralnexusstudios.nexremote.core.network.NexRemoteConnectionRepository
import com.neuralnexusstudios.nexremote.core.storage.AppPreferences
import com.neuralnexusstudios.nexremote.core.storage.CertificateStore

class AppContainer(context: Context) {
    private val appContext = context.applicationContext

    val preferences = AppPreferences(appContext)
    val certificateStore = CertificateStore(appContext)
    val connectionRepository = NexRemoteConnectionRepository(
        context = appContext,
        preferences = preferences,
        certificateStore = certificateStore,
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
