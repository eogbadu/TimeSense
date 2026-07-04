package com.timesense.app.features.now

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

@Serializable
data class NowContext(
    val greeting: String,
    val usable_minutes: Int,
    val best_task: BestTask? = null,
)

@Serializable
data class BestTask(
    val id: String,
    val title: String,
    val status: String,
    val priority: Int = 3,
    val estimated_minutes: Int? = null,
)

sealed interface NowUiState {
    data object Loading : NowUiState
    data class Loaded(val context: NowContext) : NowUiState
    data class Error(val message: String) : NowUiState
}

class NowViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<NowUiState>(NowUiState.Loading)
    val uiState: StateFlow<NowUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = NowUiState.Loading
            try {
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/now")
                    .get()
                    .build()
                val response = ApiClient.httpClient.newCall(request).execute()
                val body = response.body?.string() ?: "{}"
                if (response.isSuccessful) {
                    val ctx = ApiClient.jsonInstance.decodeFromString<NowContext>(body)
                    _uiState.value = NowUiState.Loaded(ctx)
                } else {
                    _uiState.value = NowUiState.Error("Server error ${response.code}")
                }
            } catch (e: Exception) {
                _uiState.value = NowUiState.Error(e.message ?: "Network error")
            }
        }
    }

    fun markDone(taskId: String) {
        viewModelScope.launch {
            try {
                val json = """{"status":"done"}"""
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/tasks/$taskId")
                    .patch(json.toRequestBody("application/json".toMediaType()))
                    .build()
                ApiClient.httpClient.newCall(request).execute()
            } finally {
                load()
            }
        }
    }
}
