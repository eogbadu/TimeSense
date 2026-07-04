package com.timesense.app.features.today

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.timesense.app.core.design.Elevation
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

@Composable
fun TimelineCard(
    task: TimelineTask,
    visualState: TimelineVisualState,
    modifier: Modifier = Modifier
) {
    val alpha = if (visualState == TimelineVisualState.PAST) 0.5f else 1f
    val isCurrent = visualState == TimelineVisualState.CURRENT
    val accent = MaterialTheme.colorScheme.primary

    Card(
        modifier = modifier
            .fillMaxWidth()
            .alpha(alpha),
        shape = RoundedCornerShape(Radius.md),
        border = if (isCurrent) BorderStroke(2.dp, accent) else null,
        colors = CardDefaults.cardColors(
            containerColor = if (isCurrent)
                accent.copy(alpha = 0.08f)
            else
                MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card)
    ) {
        Row(
            modifier = Modifier.padding(Spacing.md),
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.md)
        ) {
            TimeColumn(task = task, isCurrent = isCurrent)
            Divider(
                modifier = Modifier
                    .height(48.dp)
                    .width(1.dp),
                color = if (isCurrent) accent else accent.copy(alpha = 0.3f)
            )
            ContentColumn(task = task, visualState = visualState, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun TimeColumn(task: TimelineTask, isCurrent: Boolean) {
    val accent = MaterialTheme.colorScheme.primary
    val timeFmt = DateTimeFormatter.ofPattern("HH:mm")
    Column(
        modifier = Modifier.width(52.dp),
        horizontalAlignment = Alignment.End
    ) {
        task.scheduled_start?.let { raw ->
            runCatching { OffsetDateTime.parse(raw) }.getOrNull()?.let { dt ->
                Text(
                    text = dt.format(timeFmt),
                    style = MaterialTheme.typography.labelMedium,
                    color = if (isCurrent) accent else MaterialTheme.colorScheme.onSurface
                )
            }
        }
        task.scheduled_end?.let { raw ->
            runCatching { OffsetDateTime.parse(raw) }.getOrNull()?.let { dt ->
                Text(
                    text = dt.format(timeFmt),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun ContentColumn(task: TimelineTask, visualState: TimelineVisualState, modifier: Modifier = Modifier) {
    val isDone = task.status == "done" || visualState == TimelineVisualState.DONE
    Column(modifier = modifier) {
        Text(
            text = task.title,
            style = MaterialTheme.typography.bodyMedium,
            color = if (visualState == TimelineVisualState.PAST)
                MaterialTheme.colorScheme.onSurfaceVariant
            else
                MaterialTheme.colorScheme.onSurface,
            textDecoration = if (isDone) TextDecoration.LineThrough else null,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
        task.estimated_minutes?.let { mins ->
            Text(
                text = "$mins min",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
