package com.timesense.app.widgets

import android.content.Context
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
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
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Shows the next scheduled event today. Read-only: only renders whatever TodayViewModel last
 * wrote via [updateNextEvent]/[clearNextEvent] after a successful /timeline/today call.
 */
class NextEventWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        provideContent {
            val prefs = currentState<Preferences>()
            val title = prefs[titleKey]
            val startMillis = prefs[startMillisKey]

            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .background(WidgetSurface)
                    .padding(12.dp)
            ) {
                Text(
                    "NEXT UP",
                    style = TextStyle(fontSize = 11.sp, color = WidgetTextSecondary)
                )
                if (title != null && startMillis != null) {
                    Text(
                        title,
                        maxLines = 2,
                        style = TextStyle(
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = WidgetTextPrimary
                        )
                    )
                    Text(
                        formatTime(startMillis),
                        style = TextStyle(fontSize = 12.sp, color = WidgetTextSecondary)
                    )
                } else {
                    Text(
                        "Nothing scheduled",
                        style = TextStyle(fontSize = 14.sp, color = WidgetTextSecondary)
                    )
                }
            }
        }
    }

    companion object {
        internal val titleKey = stringPreferencesKey("next_event_title")
        internal val startMillisKey = longPreferencesKey("next_event_start_millis")

        private fun formatTime(epochMillis: Long): String =
            SimpleDateFormat("h:mm a", Locale.getDefault()).format(Date(epochMillis))

        suspend fun updateNextEvent(context: Context, title: String, startMillis: Long) {
            forEachGlanceId(context) { id ->
                updateAppWidgetState(context, id) { mutablePrefs ->
                    mutablePrefs[titleKey] = title
                    mutablePrefs[startMillisKey] = startMillis
                }
            }
            NextEventWidget().updateAll(context)
        }

        suspend fun clearNextEvent(context: Context) {
            forEachGlanceId(context) { id ->
                updateAppWidgetState(context, id) { mutablePrefs ->
                    mutablePrefs.remove(titleKey)
                    mutablePrefs.remove(startMillisKey)
                }
            }
            NextEventWidget().updateAll(context)
        }

        private suspend fun forEachGlanceId(context: Context, action: suspend (GlanceId) -> Unit) {
            val manager = GlanceAppWidgetManager(context)
            manager.getGlanceIds(NextEventWidget::class.java).forEach { action(it) }
        }
    }
}

class NextEventWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = NextEventWidget()
}
