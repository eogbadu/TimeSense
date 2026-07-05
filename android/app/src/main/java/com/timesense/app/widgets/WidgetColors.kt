package com.timesense.app.widgets

import androidx.compose.ui.graphics.Color
import androidx.glance.color.ColorProvider

/**
 * Mirrors ui.theme.Theme.kt's literal color values (kept private there) so widgets get the same
 * day/night palette as the rest of the app without needing a Glance Material3 theme dependency.
 */
internal val WidgetSurface = ColorProvider(day = Color(0xFFFFFFFF), night = Color(0xFF1C1C2E))
internal val WidgetTextPrimary = ColorProvider(day = Color(0xFF1A1A2E), night = Color(0xFFECEBF5))
internal val WidgetTextSecondary = ColorProvider(day = Color(0xFF6B6880), night = Color(0xFFA8A4C0))
