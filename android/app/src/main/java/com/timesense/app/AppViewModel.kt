package com.timesense.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import com.timesense.app.core.auth.AuthRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import okhttp3.Request

@Serializable
private data class Entitlement(val is_premium: Boolean = false)

data class AppUiState(
    val isAuthenticated: Boolean = false,
    val isPremium: Boolean = false,
    val isNewUser: Boolean = false
)

class AppViewModel(
    private val authRepository: AuthRepository = AuthRepository()
) : ViewModel() {

    private val _isPremium = MutableStateFlow(false)

    init {
        // Load the real Premium entitlement (active subscription or 14-day intro trial) on sign-in.
        viewModelScope.launch {
            authRepository.authStateFlow.collect { user ->
                if (user != null) refreshEntitlement() else _isPremium.value = false
            }
        }
    }

    val uiState: StateFlow<AppUiState> =
        combine(authRepository.authStateFlow, _isPremium) { user, isPremium ->
            AppUiState(
                isAuthenticated = user != null,
                isPremium = isPremium,
                isNewUser = false   // new user detection wired in TIME-021
            )
        }.stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = AppUiState(isAuthenticated = authRepository.currentUser != null)
        )

    private suspend fun refreshEntitlement() {
        try {
            val premium = withContext(Dispatchers.IO) {
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/subscriptions/me/entitlement")
                    .get()
                    .build()
                ApiClient.httpClient.newCall(request).execute().use { response ->
                    val body = response.body?.string() ?: "{}"
                    if (response.isSuccessful) {
                        ApiClient.jsonInstance.decodeFromString<Entitlement>(body).is_premium
                    } else {
                        null
                    }
                }
            }
            // Keep the last known value on a transient failure rather than downgrading the user.
            if (premium != null) _isPremium.value = premium
        } catch (_: Exception) {
            // Network error — leave isPremium unchanged.
        }
    }

    fun signOut() {
        authRepository.signOut()
    }
}
