package com.timesense.app.widgets

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.background
import androidx.glance.appwidget.provideContent
import androidx.glance.appwidget.state.updateAppWidgetState
import androidx.glance.appwidget.updateAll
import androidx.glance.currentState
import androidx.glance.layout.Column
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.padding
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle

/**
 * Shows usable minutes remaining today. Read-only: it never fetches anything itself — it only
 * renders whatever NowViewModel last wrote via [updateUsableMinutes] after a successful /now call.
 */
class UsableTimeWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        provideContent {
            val prefs = currentState<Preferences>()
            val hasSynced = prefs[hasSyncedKey] ?: false
            val minutes = prefs[usableMinutesKey] ?: 0

            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .background(WidgetSurface)
                    .padding(12.dp)
            ) {
                Text(
                    "USABLE TIME",
                    style = TextStyle(fontSize = 11.sp, color = WidgetTextSecondary)
                )
                if (hasSynced) {
                    Text(
                        formatMinutes(minutes),
                        style = TextStyle(
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold,
                            color = WidgetTextPrimary
                        )
                    )
                    Text(
                        "left today",
                        style = TextStyle(fontSize = 12.sp, color = WidgetTextSecondary)
                    )
                } else {
                    Text(
                        "Open TimeSense",
                        style = TextStyle(fontSize = 14.sp, color = WidgetTextSecondary)
                    )
                }
            }
        }
    }

    companion object {
        internal val usableMinutesKey = intPreferencesKey("usable_minutes")
        internal val hasSyncedKey = booleanPreferencesKey("has_synced")

        private fun formatMinutes(minutes: Int): String {
            if (minutes <= 0) return "0m"
            val hours = minutes / 60
            val mins = minutes % 60
            return when {
                hours == 0 -> "${mins}m"
                mins == 0 -> "${hours}h"
                else -> "${hours}h ${mins}m"
            }
        }

        suspend fun updateUsableMinutes(context: Context, minutes: Int) {
            val manager = GlanceAppWidgetManager(context)
            val glanceIds = manager.getGlanceIds(UsableTimeWidget::class.java)
            glanceIds.forEach { id ->
                updateAppWidgetState(context, id) { mutablePrefs ->
                    mutablePrefs[usableMinutesKey] = minutes
                    mutablePrefs[hasSyncedKey] = true
                }
            }
            UsableTimeWidget().updateAll(context)
        }
    }
}

class UsableTimeWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = UsableTimeWidget()
}
