import SwiftUI

struct InsightsView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignTokens.Spacing.lg) {
                    if appState.isPremium {
                        InsightsSummarySection()
                    } else {
                        InsightsPremiumGate()
                    }
                }
                .padding(.horizontal, DesignTokens.Spacing.md)
                .padding(.top, DesignTokens.Spacing.sm)
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Insights")
            .navigationBarTitleDisplayMode(.large)
        }
    }
}

private struct InsightsSummarySection: View {
    var body: some View {
        EmptyStateView(
            icon: "chart.bar.fill",
            title: "Not enough data yet",
            message: "Check back after a few days of capturing."
        )
    }
}

private struct InsightsPremiumGate: View {
    var body: some View {
        VStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: "lock.fill")
                .font(.system(size: 40))
                .foregroundColor(DesignTokens.Color.accent)

            Text("Insights require Premium")
                .font(DesignTokens.Typography.title2)
                .foregroundColor(DesignTokens.Color.textPrimary)

            Text("Upgrade to see trends, patterns, and focus scores.")
                .font(DesignTokens.Typography.callout)
                .foregroundColor(DesignTokens.Color.textSecondary)
                .multilineTextAlignment(.center)

            Button("Upgrade") { /* paywall — TIME-020 */ }
                .primaryButtonStyle()
        }
        .padding(DesignTokens.Spacing.xl)
        .cardStyle()
        .padding(.top, DesignTokens.Spacing.xxl)
    }
}
