package com.timesense.app.features.today

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import com.timesense.app.widgets.NextEventWidget
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

/** Pure, unit-testable selection of the widget's "next event": the earliest non-done task
 *  that hasn't ended yet. Kept free of Android/ViewModel dependencies so it can run as a plain
 *  JVM unit test. */
fun nextUpcomingEvent(tasks: List<TimelineTask>, now: LocalDateTime): TimelineTask? {
    return tasks
        .asSequence()
        .filter { it.status != "done" }
        .mapNotNull { task ->
            val start = task.scheduled_start?.let(::parseLocalDateTime) ?: return@mapNotNull null
            val end = task.scheduled_end?.let(::parseLocalDateTime) ?: start
            if (end.isBefore(now)) null else task to start
        }
        .minByOrNull { it.second }
        ?.first
}

private fun parseLocalDateTime(iso: String): LocalDateTime? =
    runCatching { OffsetDateTime.parse(iso).toLocalDateTime() }.getOrNull()

class TodayViewModel(application: Application) : AndroidViewModel(application) {
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
                    updateWidget(tasks)
                } else {
                    _uiState.value = TodayUiState.Error("Server error ${response.code}")
                }
            } catch (e: Exception) {
                _uiState.value = TodayUiState.Error(e.message ?: "Network error")
            }
        }
    }

    private suspend fun updateWidget(tasks: List<TimelineTask>) {
        val next = nextUpcomingEvent(tasks, LocalDateTime.now())
        val context = getApplication<Application>()
        if (next != null) {
            val startMillis = next.scheduled_start
                ?.let { runCatching { OffsetDateTime.parse(it).toInstant().toEpochMilli() }.getOrNull() }
            if (startMillis != null) {
                NextEventWidget.updateNextEvent(context, next.title, startMillis)
            } else {
                NextEventWidget.clearNextEvent(context)
            }
        } else {
            NextEventWidget.clearNextEvent(context)
        }
    }

    fun visualState(task: TimelineTask): TimelineVisualState {
        if (task.status == "done") return TimelineVisualState.DONE
        val now = LocalDateTime.now()
        val start = task.scheduled_start?.let(::parseLocalDateTime)
        val end = task.scheduled_end?.let(::parseLocalDateTime)
        return when {
            end != null && end.isBefore(now) -> TimelineVisualState.PAST
            start != null && end != null && !start.isAfter(now) && !now.isAfter(end) -> TimelineVisualState.CURRENT
            start != null && start.isBefore(now) && end == null -> TimelineVisualState.CURRENT
            else -> TimelineVisualState.FUTURE
        }
    }
}
