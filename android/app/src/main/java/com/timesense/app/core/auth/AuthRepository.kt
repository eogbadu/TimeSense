package com.timesense.app.core.auth

import com.google.firebase.auth.AuthCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.timesense.app.core.api.ApiClient
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await

/**
 * Single source of truth for Firebase auth state.
 * Emits the current [FirebaseUser] (or null) via [authStateFlow].
 * All sign-in paths call [pushTokenToApiClient] after success.
 */
class AuthRepository {
    private val auth = FirebaseAuth.getInstance()

    val authStateFlow: Flow<FirebaseUser?> = callbackFlow {
        val listener = FirebaseAuth.AuthStateListener { trySend(it.currentUser) }
        auth.addAuthStateListener(listener)
        awaitClose { auth.removeAuthStateListener(listener) }
    }

    val currentUser: FirebaseUser? get() = auth.currentUser

    suspend fun signInWithCredential(credential: AuthCredential): FirebaseUser {
        val result = auth.signInWithCredential(credential).await()
        val user = result.user ?: throw AuthException("Sign-in returned no user.")
        pushTokenToApiClient(user)
        return user
    }

    suspend fun signInWithEmail(email: String, password: String): FirebaseUser {
        val result = auth.signInWithEmailAndPassword(email, password).await()
        val user = result.user ?: throw AuthException("Sign-in returned no user.")
        pushTokenToApiClient(user)
        return user
    }

    suspend fun createAccount(email: String, password: String): FirebaseUser {
        val result = auth.createUserWithEmailAndPassword(email, password).await()
        val user = result.user ?: throw AuthException("Account creation returned no user.")
        pushTokenToApiClient(user)
        return user
    }

    suspend fun sendPasswordReset(email: String) {
        auth.sendPasswordResetEmail(email).await()
    }

    fun signOut() {
        auth.signOut()
        ApiClient.setAuthToken(null)
    }

    suspend fun freshToken(): String {
        val user = auth.currentUser ?: throw AuthException("Not authenticated.")
        return user.getIdToken(false).await().token
            ?: throw AuthException("Could not retrieve ID token.")
    }

    private suspend fun pushTokenToApiClient(user: FirebaseUser) {
        val token = user.getIdToken(false).await().token ?: return
        ApiClient.setAuthToken(token)
    }
}

class AuthException(message: String) : Exception(message)
