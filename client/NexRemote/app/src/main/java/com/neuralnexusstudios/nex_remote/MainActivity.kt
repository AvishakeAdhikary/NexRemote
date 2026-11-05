package com.neuralnexusstudios.nex_remote

import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.neuralnexusstudios.nex_remote.core.model.ThemeMode
import com.neuralnexusstudios.nex_remote.ui.NexRemoteApp
import com.neuralnexusstudios.nex_remote.ui.theme.NexRemoteTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(SystemBarStyle.dark(Color.TRANSPARENT), SystemBarStyle.dark(Color.TRANSPARENT))
        val app = application as NexRemoteApplication
        setContent {
            val settings by app.appContainer.preferences.settings.collectAsState()
            val systemDark = isSystemInDarkTheme()
            val dark = when (settings.themeMode) {
                ThemeMode.Dark -> true
                ThemeMode.Light -> false
                ThemeMode.System -> systemDark
            }
            // Status/navigation bar icons follow the in-app theme, not just the system one.
            LaunchedEffect(dark) {
                val style = if (dark) {
                    SystemBarStyle.dark(Color.TRANSPARENT)
                } else {
                    SystemBarStyle.light(Color.TRANSPARENT, Color.TRANSPARENT)
                }
                enableEdgeToEdge(style, style)
            }
            NexRemoteTheme(mode = settings.themeMode) {
                NexRemoteApp(appContainer = app.appContainer)
            }
        }
    }
}
