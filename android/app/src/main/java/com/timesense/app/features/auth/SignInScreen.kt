package com.timesense.app.features.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.timesense.app.R
import com.timesense.app.core.design.Radius
import com.timesense.app.core.design.Spacing

@Composable
fun SignInScreen(
    viewModel: AuthViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var showEmailForm by remember { mutableStateOf(false) }
    var isCreatingAccount by remember { mutableStateOf(false) }

    LaunchedEffect(uiState.error) {
        // Error shown inline; auto-clear after user takes action
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.md),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(Spacing.md)
        ) {
            Spacer(Modifier.height(Spacing.xxl))

            // Brand header
            Icon(
                painter = painterResource(R.drawable.ic_tab_now),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(bottom = Spacing.xs)
            )
            Text("TimeSense", style = MaterialTheme.typography.headlineLarge)
            Text(
                "Your personal time assistant",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(Modifier.height(Spacing.lg))

            // Google sign-in
            OutlinedButton(
                onClick = { viewModel.signInWithGoogle(context) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(Radius.pill)
            ) {
                Text("Continue with Google", style = MaterialTheme.typography.labelLarge)
            }

            // Divider
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm)
            ) {
                HorizontalDivider(modifier = Modifier.weight(1f))
                Text("or", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                HorizontalDivider(modifier = Modifier.weight(1f))
            }

            if (showEmailForm) {
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Email") },
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    singleLine = true,
                    shape = RoundedCornerShape(Radius.md)
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Password") },
                    modifier = Modifier.fillMaxWidth(),
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    singleLine = true,
                    shape = RoundedCornerShape(Radius.md)
                )
                Button(
                    onClick = {
                        if (isCreatingAccount) viewModel.createAccount(email, password)
                        else viewModel.signInWithEmail(email, password)
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = email.isNotBlank() && password.length >= 6 && !uiState.isLoading,
                    shape = RoundedCornerShape(Radius.pill)
                ) {
                    Text(if (isCreatingAccount) "Create Account" else "Sign In")
                }
                TextButton(onClick = { isCreatingAccount = !isCreatingAccount }) {
                    Text(
                        if (isCreatingAccount) "Already have an account? Sign in"
                        else "New here? Create account"
                    )
                }
            } else {
                TextButton(onClick = { showEmailForm = true }) {
                    Text("Continue with Email", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }

            if (uiState.isLoading) {
                CircularProgressIndicator()
            }

            uiState.error?.let { err ->
                Text(
                    err,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                    textAlign = TextAlign.Center
                )
            }

            Spacer(Modifier.height(Spacing.xxl))
        }
    }
}
