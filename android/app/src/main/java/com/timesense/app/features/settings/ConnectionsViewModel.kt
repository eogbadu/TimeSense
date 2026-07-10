package com.timesense.app.features.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.timesense.app.core.api.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import okhttp3.Request

@Serializable
private data class AuthorizeResponse(val authorize_url: String)

sealed interface ConnStatus {
    data object Idle : ConnStatus
    data object Connecting : ConnStatus
    data class Failed(val message: String) : ConnStatus
}

/**
 * Fetches the provider consent URL from /api/v1/integrations/{provider}/authorize and emits it for
 * the screen to open in the browser. The backend does the code→token exchange and redirects to
 * timesense://integrations/connected (handled by MainActivity's deep-link filter).
 */
class ConnectionsViewModel : ViewModel() {

    private val _open = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val open: SharedFlow<String> = _open.asSharedFlow()

    private val _status = MutableStateFlow<Map<String, ConnStatus>>(emptyMap())
    val status: StateFlow<Map<String, ConnStatus>> = _status.asStateFlow()

    fun statusFor(provider: String): ConnStatus = _status.value[provider] ?: ConnStatus.Idle

    fun connect(provider: String) {
        setStatus(provider, ConnStatus.Connecting)
        viewModelScope.launch {
            try {
                val url = withContext(Dispatchers.IO) {
                    val request = Request.Builder()
                        .url("${ApiClient.baseUrl}/api/v1/integrations/$provider/authorize")
                        .get()
                        .build()
                    ApiClient.httpClient.newCall(request).execute().use { response ->
                        when (response.code) {
                            403 -> throw ConnectError("Premium required.")
                            503 -> throw ConnectError("Not available yet.")
                        }
                        if (!response.isSuccessful) throw ConnectError("Couldn't connect. Try again.")
                        val body = response.body?.string() ?: "{}"
                        ApiClient.jsonInstance.decodeFromString<AuthorizeResponse>(body).authorize_url
                    }
                }
                _open.emit(url)
                // The browser is now open; the result returns via the deep link, so reset to Idle.
                setStatus(provider, ConnStatus.Idle)
            } catch (e: ConnectError) {
                setStatus(provider, ConnStatus.Failed(e.message ?: "Couldn't connect."))
            } catch (e: Exception) {
                setStatus(provider, ConnStatus.Failed("Couldn't connect. Try again."))
            }
        }
    }

    private fun setStatus(provider: String, status: ConnStatus) {
        _status.value = _status.value.toMutableMap().apply { put(provider, status) }
    }

    private class ConnectError(message: String) : Exception(message)
}
