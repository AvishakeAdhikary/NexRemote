package com.neuralnexusstudios.nex_remote

import android.app.Application
import com.neuralnexusstudios.nex_remote.core.AppContainer

class NexRemoteApplication : Application() {
    lateinit var appContainer: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        appContainer = AppContainer(this)
    }
}
