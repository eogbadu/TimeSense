import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var authService: AuthService
    @StateObject private var healthService = HealthService()

    @State private var showDeleteConfirm = false
    @State private var deleting = false

    var body: some View {
        NavigationStack {
            List {
                Section("AI Planning") {
                    NavigationLink(destination: LearnedAssumptionsView()) {
                        SettingsRowLabel(icon: "brain.head.profile", title: "Learned Patterns", tint: .teal)
                    }
                    NavigationLink { WorkingHoursSettingsView() } label: {
                        SettingsRowLabel(icon: "clock.fill", title: "Working Hours", tint: .indigo)
                    }
                    NavigationLink { NotificationsSettingsView() } label: {
                        SettingsRowLabel(icon: "bell.fill", title: "Notification Timing", tint: .red)
                    }
                }

                Section("Integrations") {
                    NavigationLink { CalendarSettingsView() } label: {
                        SettingsRowLabel(icon: "calendar", title: "Calendar", tint: .green)
                    }
                    NavigationLink { PlacesSettingsView() } label: {
                        SettingsRowLabel(icon: "location.fill", title: "Location & Places", tint: .blue)
                    }
                    HealthConnectRow(healthService: healthService)
                }

                Section("Privacy") {
                    NavigationLink { PrivacyConsentView() } label: {
                        SettingsRowLabel(icon: "hand.raised.fill", title: "Privacy & Consent", tint: .orange)
                    }
                    Button(role: .destructive) {
                        showDeleteConfirm = true
                    } label: {
                        HStack(spacing: DesignTokens.Spacing.md) {
                            SettingsRowLabel(icon: "trash.fill", title: "Delete My Data", tint: .red)
                            Spacer()
                            if deleting { ProgressView() }
                        }
                    }
                }

                Section("Account") {
                    NavigationLink { ProfileSettingsView() } label: {
                        SettingsRowLabel(icon: "person.circle", title: "Profile", tint: .blue)
                    }
                    NavigationLink { SubscriptionSettingsView() } label: {
                        SettingsRowLabel(icon: "crown.fill", title: "Subscription", tint: .yellow)
                    }
                    NavigationLink { AppearanceSettingsView() } label: {
                        SettingsRowLabel(icon: "paintbrush.fill", title: "Appearance", tint: .purple)
                    }
                    NavigationLink { AboutSettingsView() } label: {
                        SettingsRowLabel(icon: "info.circle", title: "About TimeSense", tint: .gray)
                    }
                    LabeledContent("Version", value: "0.1.0")
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }

                Section {
                    Button(role: .destructive) {
                        authService.signOut()
                    } label: {
                        Text("Sign Out")
                            .frame(maxWidth: .infinity)
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(CosmicBackground())
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .alert("Delete your account?", isPresented: $showDeleteConfirm) {
                Button("Cancel", role: .cancel) {}
                Button("Delete everything", role: .destructive) {
                    Task { await deleteAccount() }
                }
            } message: {
                Text("This permanently erases your account and all your data. This cannot be undone.")
            }
        }
    }

    private func deleteAccount() async {
        deleting = true
        defer { deleting = false }
        try? await APIClient.shared.delete("/api/v1/privacy/account?confirm=true")
        authService.signOut()   // drop the local session → returns to sign-in
    }
}

/// Icon + title — used inside a `NavigationLink`, which draws its own disclosure indicator.
private struct SettingsRowLabel: View {
    let icon: String
    let title: String
    let tint: SwiftUI.Color

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: icon)
                .foregroundColor(.white)
                .frame(width: 28, height: 28)
                .background(tint)
                .cornerRadius(6)
            Text(title)
                .font(DesignTokens.Typography.body)
                .foregroundColor(DesignTokens.Color.textPrimary)
        }
    }
}

/// Tappable row that requests Apple Health access and syncs the latest sleep to the backend.
private struct HealthConnectRow: View {
    @ObservedObject var healthService: HealthService

    var body: some View {
        Button {
            Task { await healthService.connectAndSync() }
        } label: {
            HStack(spacing: DesignTokens.Spacing.md) {
                SettingsRowLabel(icon: "heart.fill", title: "Connect Apple Health", tint: .pink)
                Spacer()
                statusView
            }
        }
        .buttonStyle(.plain)
        .disabled(isBusy)
    }

    private var isBusy: Bool {
        healthService.state == .requesting || healthService.state == .syncing
    }

    @ViewBuilder
    private var statusView: some View {
        switch healthService.state {
        case .requesting, .syncing:
            ProgressView()
        case .synced:
            Image(systemName: "checkmark.circle.fill").foregroundColor(DesignTokens.Color.success)
        case .noData:
            Text("No sleep data")
                .font(DesignTokens.Typography.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
        case .unavailable:
            Text("Unavailable")
                .font(DesignTokens.Typography.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
        case .error:
            Image(systemName: "exclamationmark.triangle.fill").foregroundColor(DesignTokens.Color.destructive)
        case .idle:
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
        }
    }
}
