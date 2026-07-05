import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var healthService = HealthService()

    var body: some View {
        NavigationStack {
            List {
                Section("Account") {
                    SettingsRow(icon: "person.circle", title: "Profile", tint: .blue)
                    SettingsRow(icon: "crown.fill", title: "Subscription", tint: .yellow)
                }

                Section("Preferences") {
                    SettingsRow(icon: "bell.fill", title: "Notifications", tint: .red)
                    SettingsRow(icon: "calendar", title: "Calendar", tint: .green)
                    SettingsRow(icon: "paintbrush.fill", title: "Appearance", tint: .purple)
                    NavigationLink(destination: LearnedAssumptionsView()) {
                        SettingsRowLabel(icon: "brain.head.profile", title: "Learned Assumptions", tint: .teal)
                    }
                    HealthConnectRow(healthService: healthService)
                }

                Section("Privacy") {
                    SettingsRow(icon: "hand.raised.fill", title: "Privacy & Consent", tint: .orange)
                    SettingsRow(icon: "trash.fill", title: "Delete My Data", tint: .red)
                }

                Section("About") {
                    SettingsRow(icon: "info.circle", title: "About TimeSense", tint: .gray)
                    LabeledContent("Version", value: "0.1.0")
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            }
            .scrollContentBackground(.hidden)
            .background(DesignTokens.Color.background)
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
        }
    }
}

private struct SettingsRow: View {
    let icon: String
    let title: String
    let tint: SwiftUI.Color

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            SettingsRowLabel(icon: icon, title: title, tint: tint)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
        }
    }
}

/// Icon + title only, no chevron — used inside a real `NavigationLink`, which draws its own
/// disclosure indicator (unlike `SettingsRow`'s manually-drawn one on the placeholder rows above).
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
