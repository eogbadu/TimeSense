package com.timesense.app.features.today

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
fun TodayScreen(
    viewModel: TodayViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Today", style = MaterialTheme.typography.headlineMedium) })
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when (val state = uiState) {
                is TodayUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                is TodayUiState.Error -> {
                    EmptyState(
                        icon = Icons.Filled.CalendarMonth,
                        title = "Couldn't load today",
                        message = state.message,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                is TodayUiState.Loaded -> {
                    if (state.tasks.isEmpty()) {
                        EmptyState(
                            icon = Icons.Filled.CalendarMonth,
                            title = "Nothing scheduled today",
                            message = "Use Capture to add tasks.",
                            modifier = Modifier.align(Alignment.Center)
                        )
                    } else {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
                            contentPadding = androidx.compose.foundation.layout.PaddingValues(
                                horizontal = Spacing.md,
                                vertical = Spacing.sm
                            )
                        ) {
                            item {
                                DayProgressCard(
                                    total = state.tasks.size,
                                    done = viewModel.doneCount
                                )
                                Spacer(Modifier.height(Spacing.xs))
                            }
                            items(state.tasks, key = { it.id }) { task ->
                                TimelineCard(
                                    task = task,
                                    visualState = viewModel.visualState(task)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DayProgressCard(total: Int, done: Int) {
    val progress = if (total == 0) 0f else done.toFloat() / total.toFloat()
    val today = LocalDate.now().format(
        DateTimeFormatter.ofPattern("MMMM d, yyyy", Locale.getDefault())
    )
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
