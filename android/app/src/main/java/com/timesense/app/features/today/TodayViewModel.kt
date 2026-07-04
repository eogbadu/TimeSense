package com.timesense.app.features.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import okhttp3.Request
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

@Serializable
data class TimelineTask(
    val id: String,
    val title: String,
    val status: String,
    val priority: Int = 3,
    val scheduled_start: String? = null,
    val scheduled_end: String? = null,
    val estimated_minutes: Int? = null,
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

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = TodayUiState.Loading
            try {
                val today = LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE)
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/timeline/today?date=$today")
                    .get()
                    .build()
                val response = ApiClient.httpClient.newCall(request).execute()
                val body = response.body?.string() ?: "[]"
                if (response.isSuccessful) {
                    val tasks = ApiClient.jsonInstance.decodeFromString<List<TimelineTask>>(body)
                    _uiState.value = TodayUiState.Loaded(tasks)
                } else {
                    _uiState.value = TodayUiState.Error("Server error ${response.code}")
                }
            } catch (e: Exception) {
                _uiState.value = TodayUiState.Error(e.message ?: "Network error")
            }
        }
    }

    fun visualState(task: TimelineTask): TimelineVisualState {
        if (task.status == "done") return TimelineVisualState.DONE
        val now = LocalDateTime.now()
        val start = task.scheduled_start?.let {
            runCatching { OffsetDateTime.parse(it).toLocalDateTime() }.getOrNull()
        }
        val end = task.scheduled_end?.let {
            runCatching { OffsetDateTime.parse(it).toLocalDateTime() }.getOrNull()
        }
        return when {
            end != null && end.isBefore(now) -> TimelineVisualState.PAST
            start != null && end != null && !start.isAfter(now) && !now.isAfter(end) -> TimelineVisualState.CURRENT
            start != null && start.isBefore(now) && end == null -> TimelineVisualState.CURRENT
            else -> TimelineVisualState.FUTURE
        }
    }
}
