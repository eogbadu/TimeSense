package com.timesense.app.features.settings

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Link
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing

private data class Connectable(val id: String, val name: String, val blurb: String, val color: Color)

private val CONNECTABLES = listOf(
    Connectable("google", "Google Calendar", "Schedule around your Google events.", Color(0xFF43A047)),
    Connectable("microsoft", "Outlook Calendar", "Schedule around your Outlook / Microsoft events.", Color(0xFF1E88E5)),
    Connectable("slack", "Slack", "Turn Slack messages into tasks you can approve.", Color(0xFF6A2C70)),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConnectionsScreen(
    isPremium: Boolean,
    onBack: () -> Unit = {},
    viewModel: ConnectionsViewModel = viewModel(),
) {
    val context = LocalContext.current
    val status by viewModel.status.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.open.collect { url ->
            runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Connections") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(padding)
                .padding(horizontal = Spacing.md),
        ) {
            Text(
                "Connect the tools you already use. TimeSense only reads what it needs, and calendar changes always ask first.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(vertical = Spacing.md),
            )

            if (!isPremium) {
                Text(
                    "Connecting apps is a Premium feature.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = Spacing.md),
                )
            } else {
                CONNECTABLES.forEach { provider ->
                    ConnectableCard(
                        provider = provider,
                        state = status[provider.id] ?: ConnStatus.Idle,
                        onConnect = { viewModel.connect(provider.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ConnectableCard(provider: Connectable, state: ConnStatus, onConnect: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xs),
        shape = RoundedCornerShape(Radius.lg),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(Spacing.md),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = provider.color,
                modifier = Modifier.size(40.dp),
            ) {
                Icon(
                    Icons.Filled.Link,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.padding(9.dp),
                )
            }
            Spacer(Modifier.width(Spacing.md))
            Column(modifier = Modifier.weight(1f)) {
                Text(provider.name, style = MaterialTheme.typography.titleMedium)
                val subtitle = when (state) {
                    is ConnStatus.Failed -> state.message
                    ConnStatus.Connecting -> "Opening sign-in…"
                    ConnStatus.Idle -> provider.blurb
                }
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (state is ConnStatus.Failed) MaterialTheme.colorScheme.error
                    else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.width(Spacing.sm))
            when (state) {
                ConnStatus.Connecting -> CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    strokeWidth = 2.dp,
                )
                else -> Button(onClick = onConnect) { Text("Connect") }
            }
        }
    }
}
