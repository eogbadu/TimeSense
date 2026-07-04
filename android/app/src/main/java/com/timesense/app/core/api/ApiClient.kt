package com.timesense.app.core.api

import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * Base API client. All network calls go through here — never instantiate OkHttpClient elsewhere.
 * Auth token injection via [setAuthToken]; called by AuthViewModel after Firebase sign-in.
 */
object ApiClient {
    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000"
    val baseUrl: String = System.getenv("API_BASE_URL") ?: DEFAULT_BASE_URL

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    @Volatile
    private var authToken: String? = null

    fun setAuthToken(token: String?) {
        authToken = token
    }

    val httpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val original = chain.request()
            val builder = original.newBuilder()
                .header("Content-Type", "application/json")
            authToken?.let { builder.header("Authorization", "Bearer $it") }
            chain.proceed(builder.build())
        }
        .build()

    val jsonInstance: Json get() = json

    inline fun <reified T> Request.Builder.jsonBody(body: T): Request.Builder {
        val bodyStr = json.encodeToString(kotlinx.serialization.serializer<T>(), body)
        return post(bodyStr.toRequestBody("application/json".toMediaType()))
    }
}

sealed class ApiError(message: String) : Exception(message) {
    data object Unauthorized : ApiError("Session expired. Please sign in again.")
    data object Forbidden : ApiError("You don't have permission to do that.")
    class Validation(val body: String) : ApiError("Invalid request: $body")
    class Server(val code: Int, val body: String) : ApiError("Server error ($code)")
}
