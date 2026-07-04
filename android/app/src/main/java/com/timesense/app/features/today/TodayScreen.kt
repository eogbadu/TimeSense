package com.timesense.app.features.today

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.components.EmptyState
import com.timesense.app.core.design.Elevation
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(viewModel: TodayViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Today", style = MaterialTheme.typography.headlineMedium) })
        }
    ) { padding ->
        when (val state = uiState) {
            is TodayUiState.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentAlignment = Alignment.Center
                ) { CircularProgressIndicator() }
            }
            is TodayUiState.Error -> {
                EmptyState(
                    icon = Icons.Filled.CalendarMonth,
                    title = "Couldn't load today",
                    message = state.message,
                    modifier = Modifier.padding(padding),
                    actionLabel = "Retry",
                    onAction = { viewModel.load() }
                )
            }
            is TodayUiState.Loaded -> {
                if (state.tasks.isEmpty()) {
                    EmptyState(
                        icon = Icons.Filled.CalendarMonth,
                        title = "Nothing scheduled today",
                        message = "Use Capture to add tasks.",
                        modifier = Modifier.padding(padding)
                    )
                } else {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(padding)
                            .padding(horizontal = Spacing.md),
                        verticalArrangement = Arrangement.spacedBy(Spacing.sm)
                    ) {
                        item {
                            Spacer(Modifier.height(Spacing.xs))
                            DayProgressCard(
                                total = viewModel.totalCount,
                                done = viewModel.doneCount
                            )
                            Spacer(Modifier.height(Spacing.sm))
                        }
                        items(state.tasks, key = { it.id }) { task ->
                            TimelineCard(task = task, visualState = viewModel.visualState(task))
                        }
                        item { Spacer(Modifier.height(Spacing.xl)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun DayProgressCard(total: Int, done: Int) {
    val today = LocalDate.now().format(DateTimeFormatter.ofPattern("MMMM d, yyyy", Locale.getDefault()))
    val progress = if (total == 0) 0f else done.toFloat() / total.toFloat()
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(Radius.lg),
        elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card)
    ) {
        Column(modifier = Modifier.padding(Spacing.md)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(today, style = MaterialTheme.typography.titleMedium)
                Text(
                    "$done of $total done",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(Modifier.height(Spacing.sm))
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
private fun TimelineCard(task: TimelineTask, visualState: TimelineVisualState) {
    val accent = MaterialTheme.colorScheme.primary
    val cardAlpha = if (visualState == TimelineVisualState.PAST) 0.5f else 1f

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .alpha(cardAlpha),
        shape = RoundedCornerShape(Radius.md),
        elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card),
        colors = CardDefaults.cardColors(
            containerColor = if (visualState == TimelineVisualState.CURRENT)
                MaterialTheme.colorScheme.primaryContainer
            else MaterialTheme.colorScheme.surface
        ),
        border = if (visualState == TimelineVisualState.CURRENT)
            androidx.compose.foundation.BorderStroke(2.dp, accent)
        else null
    ) {
        Row(
            modifier = Modifier.padding(Spacing.md),
            horizontalArrangement = Arrangement.spacedBy(Spacing.md),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Coloured left bar
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(48.dp)
                    .background(
                        color = when (visualState) {
                            TimelineVisualState.CURRENT -> accent
                            TimelineVisualState.DONE    -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.3f)
                            TimelineVisualState.PAST    -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.3f)
                            TimelineVisualState.FUTURE  -> accent.copy(alpha = 0.4f)
                        },
                        shape = RoundedCornerShape(2.dp)
                    )
            )

            // Time column
            Column(
                modifier = Modifier.width(52.dp),
                horizontalAlignment = Alignment.End
            ) {
                task.scheduledStart?.let { startStr ->
                    val hour = runCatching { java.time.Instant.parse(startStr) }
                        .getOrNull()
                        ?.let {
                            java.time.ZonedDateTime.ofInstant(it, java.time.ZoneId.systemDefault())
                                .let { zdt -> "%02d:%02d".format(zdt.hour, zdt.minute) }
                        } ?: startStr.take(5)
                    Text(
                        hour,
                        style = MaterialTheme.typography.labelSmall,
                        color = if (visualState == TimelineVisualState.CURRENT) accent
                        else MaterialTheme.colorScheme.onSurface
                    )
                }
                task.scheduledEnd?.let { endStr ->
                    val hour = runCatching { java.time.Instant.parse(endStr) }
                        .getOrNull()
                        ?.let {
                            java.time.ZonedDateTime.ofInstant(it, java.time.ZoneId.systemDefault())
                                .let { zdt -> "%02d:%02d".format(zdt.hour, zdt.minute) }
                        } ?: endStr.take(5)
                    Text(
                        hour,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Content
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = task.title,
                    style = MaterialTheme.typography.bodyLarge.copy(
                        textDecoration = if (task.status == "done") TextDecoration.LineThrough else null,
                        color = if (visualState == TimelineVisualState.PAST)
                            MaterialTheme.colorScheme.onSurfaceVariant
                        else MaterialTheme.colorScheme.onSurface
                    ),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                task.estimatedMinutes?.let {
                    Text(
                        "$it min",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}
