package com.neuralnexusstudios.nex_remote.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkScheme = darkColorScheme(
    primary = Color(0xFF7FD1FF),
    onPrimary = Color(0xFF00293C),
    secondary = Color(0xFF7DE0C6),
    onSecondary = Color(0xFF042C20),
    background = Color(0xFF09111A),
    onBackground = Color(0xFFE5F2FF),
    surface = Color(0xFF111C28),
    onSurface = Color(0xFFE5F2FF),
    surfaceVariant = Color(0xFF1A2836),
    onSurfaceVariant = Color(0xFFB5C8D8),
    error = Color(0xFFFF8F8F),
)

private val LightScheme = lightColorScheme(
    primary = Color(0xFF0F6FA5),
    onPrimary = Color.White,
    secondary = Color(0xFF0E8A67),
    onSecondary = Color.White,
    background = Color(0xFFF3F8FC),
    onBackground = Color(0xFF0C1823),
    surface = Color.White,
    onSurface = Color(0xFF0C1823),
    surfaceVariant = Color(0xFFDCE7F1),
    onSurfaceVariant = Color(0xFF425466),
    error = Color(0xFFB3261E),
)

@Composable
fun NexRemoteTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkScheme else LightScheme,
        content = content,
    )
}
