package com.neuralnexusstudios.nexremote

import android.app.Application
import com.neuralnexusstudios.nexremote.core.AppContainer

class NexRemoteApplication : Application() {
    lateinit var appContainer: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        appContainer = AppContainer(this)
    }
}
