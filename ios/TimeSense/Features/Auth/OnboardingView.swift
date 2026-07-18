import SwiftUI

/// Shown once after first sign-in. Calls POST /api/v1/users/me to create the backend profile.
struct OnboardingView: View {
    @EnvironmentObject private var authService: AuthService
    @State private var isLoading = false
    @State private var error: String? = nil

    let onComplete: () -> Void

    var body: some View {
        NavigationStack {
            VStack(spacing: DesignTokens.Spacing.xl) {
                Spacer()

                VStack(spacing: DesignTokens.Spacing.md) {
                    Image(systemName: "calendar.badge.clock")
                        .font(.system(size: 64))
                        .foregroundColor(DesignTokens.Color.accent)

                    Text("Welcome to TimeSense")
                        .font(DesignTokens.Typography.largeTitle)
                        .multilineTextAlignment(.center)

                    Text("Your personal time assistant. We'll help you stay focused on what matters without making managing your day another job.")
                        .font(DesignTokens.Typography.body)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, DesignTokens.Spacing.xl)
                }

                if let error {
                    Text(error)
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.destructive)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, DesignTokens.Spacing.md)
                }

                Spacer()

                Button(action: completeOnboarding) {
                    if isLoading {
                        ProgressView().tint(.white)
                    } else {
                        Text("Get Started")
                    }
                }
                .primaryButtonStyle()
                .padding(.horizontal, DesignTokens.Spacing.md)
                .disabled(isLoading)
                .padding(.bottom, DesignTokens.Spacing.xl)
            }
            .background(DesignTokens.Color.background)
            .navigationBarHidden(true)
        }
    }

    private func completeOnboarding() {
        isLoading = true
        error = nil
        Task {
            do {
                // Ensure fresh token before profile creation
                let token = try await authService.freshToken()
                APIClient.shared.setAuthToken(token)
                // POST profile so backend creates the user row
                let _: UserProfileResponse = try await APIClient.shared.post(
                    "/api/v1/users/profile",
                    body: EmptyBody()
                )
                onComplete()
            } catch {
                self.error = error.localizedDescription
                isLoading = false
            }
        }
    }
}

private struct EmptyBody: Encodable {}
private struct UserProfileResponse: Decodable {
    let id: String
    let email: String?
}
