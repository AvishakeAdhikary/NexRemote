package com.neuralnexusstudios.nex_remote

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.neuralnexusstudios.nex_remote.ui.NexRemoteApp
import com.neuralnexusstudios.nex_remote.ui.theme.NexRemoteTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val app = application as NexRemoteApplication
        setContent {
            NexRemoteTheme {
                NexRemoteApp(appContainer = app.appContainer)
            }
        }
    }
}
