package com.timesense.app.features.capture

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.TimeZone

@Serializable
private data class CaptureRequest(
    @SerialName("raw_input") val rawInput: String,
    @SerialName("user_timezone") val userTimezone: String,
)

@Serializable
data class CapturedTask(
    val id: String,
    val title: String,
    val status: String,
    val source: String,
    @SerialName("estimated_minutes") val estimatedMinutes: Int? = null,
)

sealed class CaptureUiState {
    object Idle : CaptureUiState()
    object Loading : CaptureUiState()
    data class Success(val title: String) : CaptureUiState()
    data class Error(val message: String) : CaptureUiState()
}

class CaptureViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<CaptureUiState>(CaptureUiState.Idle)
    val uiState: StateFlow<CaptureUiState> = _uiState.asStateFlow()

    fun submit(rawInput: String) {
        if (rawInput.isBlank()) return
        viewModelScope.launch {
            _uiState.value = CaptureUiState.Loading
            try {
                val json = ApiClient.jsonInstance
                val body = json.encodeToString(
                    CaptureRequest.serializer(),
                    CaptureRequest(
                        rawInput = rawInput,
                        userTimezone = TimeZone.getDefault().id
                    )
                )
                val request = Request.Builder()
                    .url("${ApiClient.baseUrl}/api/v1/capture")
                    .post(body.toRequestBody("application/json".toMediaType()))
                    .build()

                val token = ApiClient.httpClient.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) throw Exception("HTTP ${response.code}")
                    val responseBody = response.body?.string() ?: throw Exception("Empty response")
                    json.decodeFromString(CapturedTask.serializer(), responseBody)
                }
                _uiState.value = CaptureUiState.Success(title = token.title)
            } catch (e: Exception) {
                _uiState.value = CaptureUiState.Error(e.message ?: "Capture failed.")
            }
        }
    }

    fun reset() {
        _uiState.value = CaptureUiState.Idle
    }
}
