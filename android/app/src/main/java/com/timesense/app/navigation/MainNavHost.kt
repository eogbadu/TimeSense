package com.timesense.app.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.timesense.app.R
import com.timesense.app.features.capture.CaptureScreen
import com.timesense.app.features.insights.InsightsScreen
import com.timesense.app.features.now.NowScreen
import com.timesense.app.features.settings.SettingsScreen
import com.timesense.app.features.today.TodayScreen

@Composable
fun MainNavHost(
    isAuthenticated: Boolean,
    isPremium: Boolean
) {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    Scaffold(
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { tab ->
                    NavigationBarItem(
                        icon = {
                            Icon(
                                painter = painterResource(id = tab.iconRes),
                                contentDescription = tab.label
                            )
                        },
                        label = { Text(tab.label) },
                        selected = currentDestination?.hierarchy?.any { it.route == tab.route } == true,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Tab.NOW.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Tab.NOW.route) { NowScreen() }
            composable(Tab.TODAY.route) { TodayScreen() }
            composable(Tab.CAPTURE.route) { CaptureScreen() }
            composable(Tab.INSIGHTS.route) { InsightsScreen(isPremium = isPremium) }
            composable(Tab.SETTINGS.route) { SettingsScreen() }
        }
    }
}

enum class Tab(val route: String, val label: String, val iconRes: Int) {
    NOW("now", "Now", R.drawable.ic_tab_now),
    TODAY("today", "Today", R.drawable.ic_tab_today),
    CAPTURE("capture", "Capture", R.drawable.ic_tab_capture),
    INSIGHTS("insights", "Insights", R.drawable.ic_tab_insights),
    SETTINGS("settings", "Settings", R.drawable.ic_tab_settings),
}
