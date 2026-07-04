import SwiftUI
import AuthenticationServices

struct SignInView: View {
    @EnvironmentObject private var authService: AuthService
    @State private var email: String = ""
    @State private var password: String = ""
    @State private var showEmailForm: Bool = false
    @State private var isCreatingAccount: Bool = false
    @State private var appleCoordinator = AppleSignInCoordinator()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignTokens.Spacing.xl) {
                    Spacer().frame(height: DesignTokens.Spacing.xxl)
                    BrandHeader()
                    SocialSignInButtons(
                        onGoogle: signInWithGoogle,
                        onApple: signInWithApple
                    )
                    DividerRow()
                    if showEmailForm {
                        EmailSignInForm(
                            email: $email,
                            password: $password,
                            isCreatingAccount: $isCreatingAccount,
                            onSubmit: submitEmail,
                            onToggleMode: { isCreatingAccount.toggle() }
                        )
                    } else {
                        Button("Continue with Email") {
                            withAnimation(DesignTokens.Animation.standard) {
                                showEmailForm = true
                            }
                        }
                        .font(DesignTokens.Typography.body)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                    }

                    if authService.isLoading {
                        ProgressView()
                            .padding(.top, DesignTokens.Spacing.sm)
                    }

                    if let error = authService.error {
                        Text(error.localizedDescription)
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.destructive)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, DesignTokens.Spacing.md)
                    }

                    Spacer()
                }
                .padding(.horizontal, DesignTokens.Spacing.md)
            }
            .background(DesignTokens.Color.background)
            .navigationBarHidden(true)
        }
    }

    // MARK: – Actions

    private func signInWithGoogle() {
        guard let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let root = scene.windows.first?.rootViewController else { return }
        Task { await authService.signInWithGoogle(presenting: root) }
    }

    private func signInWithApple() {
        Task {
            do {
                if let credential = try await appleCoordinator.signIn() {
                    await authService.signInWithApple(credential: credential)
                }
            } catch { /* user cancelled or error handled by coordinator */ }
        }
    }

    private func submitEmail() {
        let trimmedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines)
        Task {
            if isCreatingAccount {
                await authService.createAccount(email: trimmedEmail, password: password)
            } else {
                await authService.signInWithEmail(email: trimmedEmail, password: password)
            }
        }
    }
}

// MARK: – Sub-views

private struct BrandHeader: View {
    var body: some View {
        VStack(spacing: DesignTokens.Spacing.sm) {
            Image(systemName: "clock.fill")
                .font(.system(size: 56))
                .foregroundColor(DesignTokens.Color.accent)
            Text("TimeSense")
                .font(DesignTokens.Typography.largeTitle)
                .foregroundColor(DesignTokens.Color.textPrimary)
            Text("Your personal time assistant")
                .font(DesignTokens.Typography.callout)
                .foregroundColor(DesignTokens.Color.textSecondary)
        }
    }
}

private struct SocialSignInButtons: View {
    let onGoogle: () -> Void
    let onApple: () -> Void

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.sm) {
            Button(action: onApple) {
                SignInButtonLabel(icon: "applelogo", text: "Continue with Apple")
            }
            .padding(.vertical, DesignTokens.Spacing.md)
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .frame(maxWidth: .infinity)
            .background(Color.black)
            .foregroundColor(.white)
            .cornerRadius(DesignTokens.Radius.pill)

            Button(action: onGoogle) {
                SignInButtonLabel(icon: "g.circle.fill", text: "Continue with Google")
            }
            .padding(.vertical, DesignTokens.Spacing.md)
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .frame(maxWidth: .infinity)
            .background(DesignTokens.Color.surface)
            .foregroundColor(DesignTokens.Color.textPrimary)
            .cornerRadius(DesignTokens.Radius.pill)
            .overlay(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.pill)
                    .stroke(DesignTokens.Color.textSecondary.opacity(0.3), lineWidth: 1)
            )
        }
    }
}

private struct SignInButtonLabel: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 18))
            Text(text)
                .font(DesignTokens.Typography.headline)
        }
    }
}

private struct DividerRow: View {
    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Rectangle().fill(DesignTokens.Color.textSecondary.opacity(0.2)).frame(height: 1)
            Text("or")
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
            Rectangle().fill(DesignTokens.Color.textSecondary.opacity(0.2)).frame(height: 1)
        }
    }
}

private struct EmailSignInForm: View {
    @Binding var email: String
    @Binding var password: String
    @Binding var isCreatingAccount: Bool
    let onSubmit: () -> Void
    let onToggleMode: () -> Void

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.md) {
            TextField("Email", text: $email)
                .keyboardType(.emailAddress)
                .autocapitalization(.none)
                .textContentType(.emailAddress)
                .padding(DesignTokens.Spacing.md)
                .background(DesignTokens.Color.surface)
                .cornerRadius(DesignTokens.Radius.md)

            SecureField("Password", text: $password)
                .textContentType(isCreatingAccount ? .newPassword : .password)
                .padding(DesignTokens.Spacing.md)
                .background(DesignTokens.Color.surface)
                .cornerRadius(DesignTokens.Radius.md)

            Button(action: onSubmit) {
                Text(isCreatingAccount ? "Create Account" : "Sign In")
                    .primaryButtonStyle()
            }
            .disabled(email.isEmpty || password.count < 6)
            .opacity(email.isEmpty || password.count < 6 ? 0.4 : 1.0)

            Button(action: onToggleMode) {
                Text(isCreatingAccount ? "Already have an account? Sign in" : "New here? Create account")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.accent)
            }
        }
    }
}
