package com.timesense.app

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.navigation.MainNavHost

@Composable
fun TimeSenseApp(
    appViewModel: AppViewModel = viewModel()
) {
    val uiState by appViewModel.uiState.collectAsStateWithLifecycle()

    // Auth routing added in TIME-020 — for now always show main nav
    MainNavHost(
        isAuthenticated = uiState.isAuthenticated,
        isPremium = uiState.isPremium
    )
}
