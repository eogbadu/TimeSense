package com.timesense.app.features.settings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TimePicker
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.components.EmptyState
import com.timesense.app.core.design.Spacing

private val routineOrder = listOf("sleep", "breakfast", "lunch", "dinner", "morning_hygiene", "evening_hygiene")

private fun routineLabel(routineType: String): String = when (routineType) {
    "sleep" -> "Sleep"
    "breakfast" -> "Breakfast"
    "lunch" -> "Lunch"
    "dinner" -> "Dinner"
    "morning_hygiene" -> "Morning Routine"
    "evening_hygiene" -> "Evening Routine"
    else -> routineType.replaceFirstChar { it.uppercase() }
}

private fun timeString(minuteOfDay: Int): String {
    val hour24 = minuteOfDay / 60
    val minute = minuteOfDay % 60
    val period = if (hour24 < 12) "AM" else "PM"
    val hour12 = when (hour24 % 12) { 0 -> 12; else -> hour24 % 12 }
    return "%d:%02d %s".format(hour12, minute, period)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LearnedAssumptionsScreen(
    onBack: () -> Unit,
    viewModel: LearnedAssumptionsViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    var editingRoutine by remember { mutableStateOf<RoutineAssumption?>(null) }

    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Learned Assumptions") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        when (val state = uiState) {
            is LearnedAssumptionsUiState.Loading -> Box(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center
            ) { CircularProgressIndicator() }

            is LearnedAssumptionsUiState.Error -> EmptyState(
                icon = Icons.Filled.ErrorOutline,
                title = "Couldn't load",
                message = state.message,
                modifier = Modifier.padding(padding)
            )

            is LearnedAssumptionsUiState.Loaded -> {
                val sorted = state.routines.sortedBy { routineOrder.indexOf(it.routine_type).let { i -> if (i < 0) routineOrder.size else i } }
                LazyColumn(modifier = Modifier.fillMaxSize().padding(padding)) {
                    items(sorted, key = { it.routine_type }) { routine ->
                        RoutineRow(routine = routine, onClick = { editingRoutine = routine })
                        HorizontalDivider()
                    }
                }
            }
        }
    }

    editingRoutine?.let { routine ->
        EditRoutineDialog(
            routine = routine,
            onDismiss = { editingRoutine = null },
            onSave = { start, end ->
                viewModel.update(routine.routine_type, start, end)
                editingRoutine = null
            }
        )
    }
}

@Composable
private fun RoutineRow(routine: RoutineAssumption, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = Spacing.md, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(routineLabel(routine.routine_type), style = MaterialTheme.typography.bodyLarge)
                if (routine.is_customized) {
                    Text(
                        "Edited",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(start = Spacing.xs)
                    )
                }
            }
            Text(
                "${timeString(routine.start_minute)} – ${timeString(routine.end_minute)}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Icon(
            imageVector = Icons.Filled.ChevronRight,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun EditRoutineDialog(
    routine: RoutineAssumption,
    onDismiss: () -> Unit,
    onSave: (Int, Int) -> Unit
) {
    val startState = rememberTimePickerState(
        initialHour = routine.start_minute / 60,
        initialMinute = routine.start_minute % 60,
        is24Hour = false
    )
    val endState = rememberTimePickerState(
        initialHour = routine.end_minute / 60,
        initialMinute = routine.end_minute % 60,
        is24Hour = false
    )
    var editingStart by remember { mutableStateOf(true) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(routineLabel(routine.routine_type)) },
        text = {
            Column {
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    TextButton(onClick = { editingStart = true }) { Text("Starts") }
                    TextButton(onClick = { editingStart = false }) { Text("Ends") }
                }
                if (editingStart) TimePicker(state = startState) else TimePicker(state = endState)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                onSave(
                    startState.hour * 60 + startState.minute,
                    endState.hour * 60 + endState.minute
                )
            }) { Text("Save") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}
