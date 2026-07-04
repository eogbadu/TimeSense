package com.timesense.app.features.now

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.timesense.app.components.EmptyState
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NowScreen() {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Now", style = MaterialTheme.typography.headlineMedium) })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(padding)
                .padding(horizontal = Spacing.md),
            verticalArrangement = Arrangement.spacedBy(Spacing.md)
        ) {
            Spacer(Modifier.height(Spacing.xs))
            ContextSummaryCard()
            CurrentFocusCard()
            UpNextSection()
        }
    }
}

@Composable
private fun ContextSummaryCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(Radius.lg),
        elevation = CardDefaults.cardElevation(defaultElevation = com.timesense.app.core.design.Elevation.card)
    ) {
        Column(modifier = Modifier.padding(Spacing.md)) {
            Text("Good morning", style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(Spacing.xs))
            Text(
                "Here's what matters right now.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun CurrentFocusCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(Radius.lg),
        elevation = CardDefaults.cardElevation(defaultElevation = com.timesense.app.core.design.Elevation.card)
    ) {
        Column(modifier = Modifier.padding(Spacing.md)) {
            Text(
                "CURRENT FOCUS",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(Spacing.sm))
            Text(
                "No active focus block",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun UpNextSection() {
    Text(
        "UP NEXT",
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
    EmptyState(
        icon = Icons.Filled.AutoAwesome,
        title = "Nothing scheduled",
        message = "Add tasks via Capture to see them here."
    )
}
