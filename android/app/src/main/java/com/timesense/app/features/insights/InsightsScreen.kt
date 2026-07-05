package com.timesense.app.features.insights

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.NightsStay
import androidx.compose.material.icons.filled.Percent
import androidx.compose.material.icons.filled.Restaurant
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.components.EmptyState
import com.timesense.app.core.design.Elevation
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InsightsScreen(isPremium: Boolean, viewModel: InsightsViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(isPremium) {
        if (isPremium) viewModel.load()
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Insights", style = MaterialTheme.typography.headlineMedium) })
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
            if (!isPremium) {
                PremiumGateCard()
            } else {
                when (val state = uiState) {
                    is InsightsUiState.Loading -> Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center
                    ) { CircularProgressIndicator() }

                    is InsightsUiState.Error -> EmptyState(
                        icon = Icons.Filled.BarChart,
                        title = "Not enough data yet",
                        message = "Check back after a few days of capturing."
                    )

                    is InsightsUiState.Loaded -> InsightsContent(state.insight)
                }
            }
        }
    }
}

@Composable
private fun InsightsContent(insight: WeeklyInsight) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(Radius.lg),
            elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card)
        ) {
            Column(modifier = Modifier.padding(Spacing.md)) {
                Text(
                    "YOUR WEEK",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(Spacing.xs))
                Text(insight.summary_text, style = MaterialTheme.typography.bodyLarge)
            }
        }

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(Radius.lg),
            elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card)
        ) {
            Column(
                modifier = Modifier.padding(Spacing.md),
                verticalArrangement = Arrangement.spacedBy(Spacing.sm)
            ) {
                StatRow(
                    icon = Icons.Filled.CheckCircle,
                    label = "Tasks completed",
                    value = "${insight.tasks_completed} of ${insight.tasks_total}"
                )
                StatRow(
                    icon = Icons.Filled.Percent,
                    label = "Completion rate",
                    value = insight.completion_rate?.let { "${(it * 100).roundToInt()}%" } ?: "—"
                )
                insight.most_skipped_meal?.let { meal ->
                    StatRow(
                        icon = Icons.Filled.Restaurant,
                        label = "Most skipped meal",
                        value = meal.replaceFirstChar { it.uppercase() }
                    )
                }
                if (insight.late_wake_count > 0) {
                    StatRow(
                        icon = Icons.Filled.NightsStay,
                        label = "Late wake-ups",
                        value = "${insight.late_wake_count}"
                    )
                }
                if (insight.commute_confirmed_count > 0) {
                    StatRow(
                        icon = Icons.Filled.DirectionsCar,
                        label = "Commutes tracked",
                        value = "${insight.commute_confirmed_count}"
                    )
                }
            }
        }
    }
}

@Composable
private fun StatRow(icon: ImageVector, label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                label,
                modifier = Modifier.padding(start = Spacing.xs),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun PremiumGateCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(Radius.lg),
        elevation = CardDefaults.cardElevation(defaultElevation = Elevation.card)
    ) {
        Column(
            modifier = Modifier.padding(Spacing.xl),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(Spacing.md)
        ) {
            Icon(
                imageVector = Icons.Filled.Lock,
                contentDescription = null,
                modifier = Modifier.size(48.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            Text(
                "Insights require Premium",
                style = MaterialTheme.typography.titleLarge,
                textAlign = TextAlign.Center
            )
            Text(
                "Upgrade to see trends, patterns, and focus scores.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
            Button(
                onClick = { /* paywall — TIME-020 */ },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(Radius.pill)
            ) {
                Text("Upgrade")
            }
        }
    }
}
