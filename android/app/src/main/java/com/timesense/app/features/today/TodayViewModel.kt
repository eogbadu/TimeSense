package com.timesense.app.features.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.Request
import java.time.LocalDate

@Serializable
data class TimelineTask(
    val id: String,
    val title: String,
    val status: String,
    val priority: Int = 2,
    @SerialName("scheduled_start") val scheduledStart: String? = null,
    @SerialName("scheduled_end")   val scheduledEnd: String?   = null,
    @SerialName("estimated_minutes") val estimatedMinutes: Int? = null,
)

enum class TimelineVisualState { PAST, CURRENT, FUTURE, DONE }

sealed interface TodayUiState {
    data object Loading : TodayUiState
    data class Loaded(val tasks: List<TimelineTask>) : TodayUiState
    data class Error(val message: String) : TodayUiState
}

class TodayViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<TodayUiState>(TodayUiState.Loading)
    val uiState: StateFlow<TodayUiState> = _uiState.asStateFlow()

    val doneCount: Int
        get() = (_uiState.value as? TodayUiState.Loaded)?.tasks?.count { it.status == "done" } ?: 0

    val totalCount: Int
        get() = (_uiState.value as? TodayUiState.Loaded)?.tasks?.size ?: 0

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = TodayUiState.Loading
            try {
                val today = LocalDate.now().toString()
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/timeline/today?date=$today")
                    .get()
                    .build()
                val response = ApiClient.httpClient.newCall(request).execute()
                if (!response.isSuccessful) {
                    _uiState.value = TodayUiState.Error("Server error ${response.code}")
                    return@launch
                }
                val body = response.body?.string() ?: "[]"
                val tasks = Json { ignoreUnknownKeys = true }.decodeFromString<List<TimelineTask>>(body)
                _uiState.value = TodayUiState.Loaded(tasks)
            } catch (e: Exception) {
                _uiState.value = TodayUiState.Error(e.localizedMessage ?: "Failed to load timeline")
            }
        }
    }

    fun visualState(task: TimelineTask): TimelineVisualState {
        if (task.status == "done") return TimelineVisualState.DONE
        val now = java.time.Instant.now()
        val end = task.scheduledEnd?.let { runCatching { java.time.Instant.parse(it) }.getOrNull() }
        val start = task.scheduledStart?.let { runCatching { java.time.Instant.parse(it) }.getOrNull() }
        if (end != null && end.isBefore(now)) return TimelineVisualState.PAST
        if (start != null && !start.isAfter(now) && (end == null || !end.isBefore(now))) return TimelineVisualState.CURRENT
        return TimelineVisualState.FUTURE
    }
}
