package com.timesense.app.features.settings

import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.GppGood
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onLearnedAssumptionsClick: () -> Unit = {},
    onConnectionsClick: () -> Unit = {},
) {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Settings", style = MaterialTheme.typography.headlineMedium) })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(padding)
                .padding(horizontal = Spacing.md)
        ) {
            SettingsSection("Account") {
                SettingsItem(Icons.Filled.AccountCircle, "Profile", Color(0xFF1E88E5))
                SettingsItem(Icons.Filled.Star, "Subscription", Color(0xFFFFC107))
            }
            SettingsSection("Preferences") {
                SettingsItem(
                    Icons.Filled.Link,
                    "Connections",
                    Color(0xFF3949AB),
                    onClick = onConnectionsClick
                )
                SettingsItem(Icons.Filled.Notifications, "Notifications", Color(0xFFE53935))
                SettingsItem(Icons.Filled.CalendarMonth, "Calendar", Color(0xFF43A047))
                SettingsItem(Icons.Filled.Palette, "Appearance", Color(0xFF8E24AA))
                SettingsItem(
                    Icons.Filled.Psychology,
                    "Learned Assumptions",
                    Color(0xFF00897B),
                    onClick = onLearnedAssumptionsClick
                )
            }
            SettingsSection("Privacy") {
                SettingsItem(Icons.Filled.GppGood, "Privacy & Consent", Color(0xFFFB8C00))
                SettingsItem(Icons.Filled.Delete, "Delete My Data", Color(0xFFE53935))
            }
            SettingsSection("About") {
                SettingsItem(Icons.Filled.Info, "About TimeSense", Color(0xFF757575))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = Spacing.md, vertical = 14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Version", style = MaterialTheme.typography.bodyLarge)
                    Spacer(Modifier.weight(1f))
                    Text(
                        "0.1.0",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@Composable
private fun SettingsSection(title: String, content: @Composable () -> Unit) {
    Column {
        Text(
            title.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(
                start = Spacing.md,
                top = Spacing.lg,
                bottom = Spacing.xs
            )
        )
        Surface(
            shape = RoundedCornerShape(Radius.lg),
            tonalElevation = 1.dp
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                content()
            }
        }
    }
}

@Composable
private fun SettingsItem(icon: ImageVector, title: String, tint: Color, onClick: () -> Unit = {}) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = Spacing.md, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Surface(
            shape = RoundedCornerShape(6.dp),
            color = tint,
            modifier = Modifier.size(32.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.padding(4.dp)
            )
        }
        Spacer(Modifier.width(Spacing.md))
        Text(title, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        Icon(
            imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(20.dp)
        )
    }
    HorizontalDivider(modifier = Modifier.padding(start = 64.dp))
}
