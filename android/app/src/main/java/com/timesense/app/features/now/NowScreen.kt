package com.timesense.app.features.now

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.components.EmptyState
import com.timesense.app.core.design.Elevation
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NowScreen(
    viewModel: NowViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Now", style = MaterialTheme.typography.headlineMedium) })
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when (val state = uiState) {
                is NowUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                is NowUiState.Error -> {
                    EmptyState(
                        icon = Icons.Filled.AutoAwesome,
                        title = "Couldn't load",
                        message = state.message,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                is NowUiState.Loaded -> {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = Spacing.md),
                        verticalArrangement = Arrangement.spacedBy(Spacing.md)
                    ) {
                        Spacer(Modifier.height(Spacing.xs))
                        GreetingCard(
                            greeting = state.context.greeting,
                            usableMinutes = state.context.usable_minutes
                        )
                        val task = state.context.best_task
                        if (task != null) {
                            BestTaskCard(
                                task = task,
                                onAgree = { viewModel.agree(task.id) },
                                onDisagree = { viewModel.disagree(task.id) },
                                onDone = { viewModel.markDone(task.id) },
                                onSnooze = { viewModel.snooze(task.id) },
                            )
                        } else {
                            EmptyState(
                                icon = Icons.Filled.AutoAwesome,
                                title = "Nothing on your plate right now",
                                message = "Capture a task to get started."
                            )
                        }
                        Spacer(Modifier.height(Spacing.xl))
                    }
                }
            }
        }
    }
}

@Composable
private fun GreetingCard(greeting: String, usableMinutes: Int) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(Radius.lg),
        elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card)
    ) {
        Column(modifier = Modifier.padding(Spacing.md)) {
            Text(greeting, style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(Spacing.xs))
            Text(
                "$usableMinutes min available",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
private fun BestTaskCard(
    task: BestTask,
    onAgree: () -> Unit,
    onDisagree: () -> Unit,
    onDone: () -> Unit,
    onSnooze: () -> Unit,
) {
    // Reset the Agree/Disagree stage whenever the recommendation changes (keyed by task id).
    var agreed by remember(task.id) { mutableStateOf(false) }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(Radius.lg),
        elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card)
    ) {
        Column(modifier = Modifier.padding(Spacing.md)) {
            Text(
                "BEST NEXT TASK",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(Spacing.xs))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(task.title, style = MaterialTheme.typography.titleMedium)
                    task.estimated_minutes?.let { mins ->
                        Text(
                            "$mins min estimated",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                PriorityChip(priority = task.priority)
            }
            Spacer(Modifier.height(Spacing.md))
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                if (agreed) {
                    Button(onClick = onDone) { Text("Done") }
                    OutlinedButton(onClick = onSnooze) { Text("Snooze") }
                } else {
                    Button(onClick = { agreed = true; onAgree() }) { Text("Agree") }
                    OutlinedButton(
                        onClick = onDisagree,
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    ) { Text("Disagree") }
                }
            }
        }
    }
}

@Composable
private fun PriorityChip(priority: Int) {
    val label = "P$priority"
    val color = when (priority) {
        1 -> MaterialTheme.colorScheme.error
        2 -> MaterialTheme.colorScheme.tertiary
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Text(
        label,
        style = MaterialTheme.typography.labelSmall,
        color = color,
        modifier = Modifier.padding(start = Spacing.sm)
    )
}
