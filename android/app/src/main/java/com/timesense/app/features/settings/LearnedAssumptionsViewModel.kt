package com.timesense.app.features.settings

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
data class RoutineAssumption(
    val id: String,
    val routine_type: String,
    val start_minute: Int,
    val end_minute: Int,
    val is_customized: Boolean,
)

sealed interface LearnedAssumptionsUiState {
    data object Loading : LearnedAssumptionsUiState
    data class Loaded(val routines: List<RoutineAssumption>) : LearnedAssumptionsUiState
    data class Error(val message: String) : LearnedAssumptionsUiState
}

class LearnedAssumptionsViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<LearnedAssumptionsUiState>(LearnedAssumptionsUiState.Loading)
    val uiState: StateFlow<LearnedAssumptionsUiState> = _uiState.asStateFlow()

    fun load() {
        viewModelScope.launch {
            _uiState.value = LearnedAssumptionsUiState.Loading
            try {
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/routines")
                    .get()
                    .build()
                val response = ApiClient.httpClient.newCall(request).execute()
                val body = response.body?.string() ?: "[]"
                if (response.isSuccessful) {
                    val routines = ApiClient.jsonInstance.decodeFromString<List<RoutineAssumption>>(body)
                    _uiState.value = LearnedAssumptionsUiState.Loaded(routines)
                } else {
                    _uiState.value = LearnedAssumptionsUiState.Error("Server error ${response.code}")
                }
            } catch (e: Exception) {
                _uiState.value = LearnedAssumptionsUiState.Error(e.message ?: "Network error")
            }
        }
    }

    fun update(routineType: String, startMinute: Int, endMinute: Int) {
        viewModelScope.launch {
            try {
                val json = """{"start_minute":$startMinute,"end_minute":$endMinute}"""
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/routines/$routineType")
                    .patch(json.toRequestBody("application/json".toMediaType()))
                    .build()
                val response = ApiClient.httpClient.newCall(request).execute()
                val body = response.body?.string() ?: "{}"
                if (response.isSuccessful) {
                    val updated = ApiClient.jsonInstance.decodeFromString<RoutineAssumption>(body)
                    val current = _uiState.value
                    if (current is LearnedAssumptionsUiState.Loaded) {
                        _uiState.value = LearnedAssumptionsUiState.Loaded(
                            current.routines.map { if (it.routine_type == routineType) updated else it }
                        )
                    } else {
                        load()
                    }
                } else {
                    load()
                }
            } catch (e: Exception) {
                load()
            }
        }
    }
}
