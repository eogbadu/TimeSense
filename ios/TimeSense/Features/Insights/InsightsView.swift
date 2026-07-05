import SwiftUI

struct InsightsView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = InsightsViewModel()

    var body: some View {
        NavigationStack {
            Group {
                if appState.isPremium {
                    premiumBody
                } else {
                    InsightsPremiumGate()
                }
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Insights")
            .navigationBarTitleDisplayMode(.large)
        }
        .task {
            if appState.isPremium {
                await viewModel.load()
            }
        }
    }

    @ViewBuilder
    private var premiumBody: some View {
        switch viewModel.uiState {
        case .idle, .loading:
            ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
        case .error:
            EmptyStateView(
                icon: "chart.bar.fill",
                title: "Not enough data yet",
                message: "Check back after a few days of capturing."
            )
        case .loaded(let insight):
            ScrollView {
                InsightsSummarySection(insight: insight)
                    .padding(.horizontal, DesignTokens.Spacing.md)
                    .padding(.top, DesignTokens.Spacing.sm)
                    .padding(.bottom, DesignTokens.Spacing.xl)
            }
        }
    }
}

private struct InsightsSummarySection: View {
    let insight: WeeklyInsight

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
            SummaryCard(insight: insight)
            StatsGrid(insight: insight)
        }
    }
}

private struct SummaryCard: View {
    let insight: WeeklyInsight

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("YOUR WEEK")
                .sectionHeaderStyle()
            Text(insight.summaryText)
                .font(DesignTokens.Typography.body)
                .foregroundColor(DesignTokens.Color.textPrimary)
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}

private struct StatsGrid: View {
    let insight: WeeklyInsight

    private var completionRateText: String {
        guard let rate = insight.completionRate else { return "—" }
        return "\(Int((rate * 100).rounded()))%"
    }

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.sm) {
            StatRow(
                icon: "checkmark.circle",
                label: "Tasks completed",
                value: "\(insight.tasksCompleted) of \(insight.tasksTotal)"
            )
            StatRow(icon: "percent", label: "Completion rate", value: completionRateText)
            if let meal = insight.mostSkippedMeal {
                StatRow(icon: "fork.knife", label: "Most skipped meal", value: meal.capitalized)
            }
            if insight.lateWakeCount > 0 {
                StatRow(icon: "moon.zzz", label: "Late wake-ups", value: "\(insight.lateWakeCount)")
            }
            if insight.commuteConfirmedCount > 0 {
                StatRow(icon: "car", label: "Commutes tracked", value: "\(insight.commuteConfirmedCount)")
            }
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}

private struct StatRow: View {
    let icon: String
    let label: String
    let value: String

    var body: some View {
        HStack {
            Label(label, systemImage: icon)
                .font(DesignTokens.Typography.callout)
                .foregroundColor(DesignTokens.Color.textSecondary)
            Spacer()
            Text(value)
                .font(DesignTokens.Typography.callout.weight(.semibold))
                .foregroundColor(DesignTokens.Color.textPrimary)
        }
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
