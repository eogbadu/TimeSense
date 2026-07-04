package com.timesense.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.auth.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

data class AppUiState(
    val isAuthenticated: Boolean = false,
    val isPremium: Boolean = false,
    val isNewUser: Boolean = false
)

class AppViewModel(
    private val authRepository: AuthRepository = AuthRepository()
) : ViewModel() {

    val uiState: StateFlow<AppUiState> = authRepository.authStateFlow
        .map { user ->
            AppUiState(
                isAuthenticated = user != null,
                isPremium = false,  // subscription state wired in TIME-023
                isNewUser = false   // new user detection wired in TIME-021
            )
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = AppUiState(isAuthenticated = authRepository.currentUser != null)
        )

    fun signOut() {
        authRepository.signOut()
    }
}
