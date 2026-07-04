package com.timesense.app

import androidx.compose.animation.AnimatedContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.features.auth.OnboardingScreen
import com.timesense.app.features.auth.SignInScreen
import com.timesense.app.navigation.MainNavHost

@Composable
fun TimeSenseApp(
    appViewModel: AppViewModel = viewModel()
) {
    val uiState by appViewModel.uiState.collectAsStateWithLifecycle()

    AnimatedContent(targetState = uiState.isAuthenticated, label = "auth") { isAuth ->
        if (isAuth) {
            if (uiState.isNewUser) {
                OnboardingScreen(onComplete = { /* flip isNewUser — wired in TIME-021 */ })
            } else {
                MainNavHost(
                    isAuthenticated = true,
                    isPremium = uiState.isPremium
                )
            }
        } else {
            SignInScreen()
        }
    }
}
