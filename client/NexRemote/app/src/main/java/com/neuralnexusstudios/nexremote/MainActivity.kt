package com.neuralnexusstudios.nexremote

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.neuralnexusstudios.nexremote.ui.NexRemoteApp
import com.neuralnexusstudios.nexremote.ui.theme.NexRemoteTheme

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
