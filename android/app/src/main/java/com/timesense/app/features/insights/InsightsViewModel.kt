package com.timesense.app.features.insights

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import okhttp3.Request

@Serializable
data class WeeklyInsight(
    val week_start: String,
    val week_end: String,
    val tasks_completed: Int,
    val tasks_total: Int,
    val completion_rate: Double? = null,
    val most_skipped_meal: String? = null,
    val late_wake_count: Int = 0,
    val commute_confirmed_count: Int = 0,
    val feedback_done_count: Int = 0,
    val feedback_not_now_count: Int = 0,
    val summary_text: String,
)

sealed interface InsightsUiState {
    data object Loading : InsightsUiState
    data class Loaded(val insight: WeeklyInsight) : InsightsUiState
    data class Error(val message: String) : InsightsUiState
}

class InsightsViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<InsightsUiState>(InsightsUiState.Loading)
    val uiState: StateFlow<InsightsUiState> = _uiState.asStateFlow()

    fun load() {
        viewModelScope.launch {
            _uiState.value = InsightsUiState.Loading
            try {
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/insights/weekly")
                    .get()
                    .build()
                val response = ApiClient.httpClient.newCall(request).execute()
                val body = response.body?.string() ?: "{}"
                if (response.isSuccessful) {
                    val insight = ApiClient.jsonInstance.decodeFromString<WeeklyInsight>(body)
                    _uiState.value = InsightsUiState.Loaded(insight)
                } else {
                    _uiState.value = InsightsUiState.Error("Server error ${response.code}")
                }
            } catch (e: Exception) {
                _uiState.value = InsightsUiState.Error(e.message ?: "Network error")
            }
        }
    }
}
