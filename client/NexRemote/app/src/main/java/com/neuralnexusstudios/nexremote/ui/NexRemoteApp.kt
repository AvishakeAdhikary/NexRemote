package com.neuralnexusstudios.nexremote.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.neuralnexusstudios.nexremote.core.AppContainer
import com.neuralnexusstudios.nexremote.ui.screens.CameraScreen
import com.neuralnexusstudios.nexremote.ui.screens.ConnectionScreen
import com.neuralnexusstudios.nexremote.ui.screens.FileExplorerScreen
import com.neuralnexusstudios.nexremote.ui.screens.GamepadScreen
import com.neuralnexusstudios.nexremote.ui.screens.HomeScreen
import com.neuralnexusstudios.nexremote.ui.screens.LegalScreen
import com.neuralnexusstudios.nexremote.ui.screens.MediaControlScreen
import com.neuralnexusstudios.nexremote.ui.screens.ScreenShareScreen
import com.neuralnexusstudios.nexremote.ui.screens.SettingsScreen
import com.neuralnexusstudios.nexremote.ui.screens.TaskManagerScreen
import com.neuralnexusstudios.nexremote.ui.screens.TouchpadScreen

@Composable
fun NexRemoteApp(appContainer: AppContainer) {
    val navController = rememberNavController()
    val settings by appContainer.preferences.settings.collectAsState()
    val startDestination = if (settings.termsAccepted) Routes.Home else Routes.Legal

    NavHost(navController = navController, startDestination = startDestination) {
        composable(Routes.Legal) {
            LegalScreen(
                appContainer = appContainer,
                onAccepted = {
                    navController.navigate(Routes.Home) {
                        popUpTo(Routes.Legal) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.Home) {
            HomeScreen(
                appContainer = appContainer,
                onOpenConnection = { navController.navigate(Routes.Connection) },
                onOpenSettings = { navController.navigate(Routes.Settings) },
                onOpenGamepad = { navController.navigate(Routes.Gamepad) },
                onOpenTouchpad = { navController.navigate(Routes.Touchpad) },
                onOpenMedia = { navController.navigate(Routes.Media) },
                onOpenCamera = { navController.navigate(Routes.Camera) },
                onOpenScreenShare = { navController.navigate(Routes.ScreenShare) },
                onOpenFileExplorer = { navController.navigate(Routes.FileExplorer) },
                onOpenTaskManager = { navController.navigate(Routes.TaskManager) },
            )
        }
        composable(Routes.Connection) {
            ConnectionScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.Settings) {
            SettingsScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.Touchpad) {
            TouchpadScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.Media) {
            MediaControlScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.Gamepad) {
            GamepadScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.Camera) {
            CameraScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.ScreenShare) {
            ScreenShareScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.FileExplorer) {
            FileExplorerScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
        composable(Routes.TaskManager) {
            TaskManagerScreen(appContainer = appContainer, onBack = { navController.popBackStack() })
        }
    }
}

object Routes {
    const val Legal = "legal"
    const val Home = "home"
    const val Connection = "connection"
    const val Settings = "settings"
    const val Touchpad = "touchpad"
    const val Media = "media"
    const val Gamepad = "gamepad"
    const val Camera = "camera"
    const val ScreenShare = "screen-share"
    const val FileExplorer = "file-explorer"
    const val TaskManager = "task-manager"
}
