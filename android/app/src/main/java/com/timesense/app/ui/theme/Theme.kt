package com.timesense.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AccentIndigo = Color(0xFF5B4FDE)
private val AccentIndigoDark = Color(0xFF7B70F0)

private val LightColorScheme = lightColorScheme(
    primary = AccentIndigo,
    onPrimary = Color.White,
    secondary = AccentIndigo,
    background = Color(0xFFF8F8FB),
    surface = Color.White,
    onBackground = Color(0xFF1A1A2E),
    onSurface = Color(0xFF1A1A2E),
    surfaceVariant = Color(0xFFF0EFF8),
    onSurfaceVariant = Color(0xFF6B6880),
    error = Color(0xFFD32F2F),
)

private val DarkColorScheme = darkColorScheme(
    primary = AccentIndigoDark,
    onPrimary = Color.White,
    secondary = AccentIndigoDark,
    background = Color(0xFF0F0F1A),
    surface = Color(0xFF1C1C2E),
    onBackground = Color(0xFFECEBF5),
    onSurface = Color(0xFFECEBF5),
    surfaceVariant = Color(0xFF2A2A3E),
    onSurfaceVariant = Color(0xFFA8A4C0),
    error = Color(0xFFEF5350),
)

@Composable
fun TimeSenseTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = TimeSenseTypography,
        content = content
    )
}
