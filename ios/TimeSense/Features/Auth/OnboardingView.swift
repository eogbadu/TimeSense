import SwiftUI

/// Shown once after first sign-in. Calls POST /api/v1/users/me to create the backend profile.
struct OnboardingView: View {
    @EnvironmentObject private var authService: AuthService
    @ObservedObject private var location = LocationService.shared
    @State private var isLoading = false
    @State private var error: String? = nil
    /// Onboarding is two steps now: welcome, then the location ask. Location was previously only
    /// requestable from Settings ▸ Places, which onboarding never routed anyone to — so a user who
    /// never went looking had the permission undetermined forever and the whole location signal was
    /// dead for them (TIME-291).
    @State private var step: Step = .welcome

    private enum Step { case welcome, location }

    let onComplete: () -> Void

    var body: some View {
        switch step {
        case .welcome: welcomeStep
        case .location: locationStep
        }
    }

    /// Asked here rather than buried in Settings, and explained in terms of what the user gets.
    /// Skipping is a first-class option — nothing else in the app depends on it.
    private var locationStep: some View {
        NavigationStack {
            VStack(spacing: DesignTokens.Spacing.xl) {
                Spacer()
                VStack(spacing: DesignTokens.Spacing.md) {
                    Image(systemName: "location.circle.fill")
                        .font(.system(size: 64))
                        .foregroundColor(DesignTokens.Color.accent)
                    Text("Suggest errands at the right moment")
                        .font(DesignTokens.Typography.title2)
                        .multilineTextAlignment(.center)
                    Text("If TimeSense knows roughly where you are, it can tell whether an errand actually fits before your next commitment — and stop suggesting one while you're at home.")
                        .font(DesignTokens.Typography.body)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, DesignTokens.Spacing.xl)
                    Text("Only your current place is stored — never a history of where you've been.")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, DesignTokens.Spacing.xl)
                }
                Spacer()
                VStack(spacing: DesignTokens.Spacing.sm) {
                    Button("Enable location") {
                        location.requestPermission()
                        finish()
                    }
                    .primaryButtonStyle()
                    Button("Not now") { finish() }
                        .font(DesignTokens.Typography.callout)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
                .padding(.horizontal, DesignTokens.Spacing.md)
                .padding(.bottom, DesignTokens.Spacing.xl)
            }
            .background(DesignTokens.Color.background)
            .navigationBarHidden(true)
        }
    }

    private func finish() {
        location.start()
        onComplete()
    }

    private var welcomeStep: some View {
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
                isLoading = false
                step = .location
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
