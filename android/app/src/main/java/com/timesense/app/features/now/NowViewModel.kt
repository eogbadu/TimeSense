package com.timesense.app.features.now

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import com.timesense.app.widgets.UsableTimeWidget
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.time.Instant

@Serializable
data class NowContext(
    val greeting: String,
    val usable_minutes: Int,
    val best_task: BestTask? = null,
    val recommendation_event_id: String? = null,
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

class NowViewModel(application: Application) : AndroidViewModel(application) {
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
                    UsableTimeWidget.updateUsableMinutes(getApplication(), ctx.usable_minutes)
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

    /** User agrees this is the right next action — record it (no reload; the buttons swap in place). */
    fun agree(taskId: String) = sendFeedback(taskId, "agree", reload = false)

    /** User disagrees — record it and reload so a different (demoted, not hidden) action surfaces. */
    fun disagree(taskId: String) = sendFeedback(taskId, "disagree")

    /** Snooze the current best task for a few hours. */
    fun snooze(taskId: String) =
        sendFeedback(taskId, "snooze", snoozeUntil = Instant.now().plusSeconds(3 * 3600L).toString())

    private fun sendFeedback(
        taskId: String,
        signal: String,
        snoozeUntil: String? = null,
        reload: Boolean = true,
    ) {
        val eventId = (_uiState.value as? NowUiState.Loaded)?.context?.recommendation_event_id
        viewModelScope.launch {
            try {
                val json = ApiClient.jsonInstance.encodeToString(
                    FeedbackRequest.serializer(),
                    FeedbackRequest(
                        task_id = taskId, signal = signal, snooze_until = snoozeUntil,
                        recommendation_event_id = eventId,
                    ),
                )
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/recommendations/feedback")
                    .post(json.toRequestBody("application/json".toMediaType()))
                    .build()
                ApiClient.httpClient.newCall(request).execute()
            } catch (_: Exception) {
                // ignore; a reload reflects the true state
            } finally {
                if (reload) load()
            }
        }
    }
}

@Serializable
private data class FeedbackRequest(
    val task_id: String,
    val signal: String,
    val snooze_until: String? = null,
    val recommendation_event_id: String? = null,
)
