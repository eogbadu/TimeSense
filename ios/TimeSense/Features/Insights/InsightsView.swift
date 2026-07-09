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
            .background(CosmicBackground())
            .navigationTitle("Insights")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Image(systemName: "crown.fill").foregroundColor(DesignTokens.Color.accent)
                }
            }
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

/// Locked Insights — previews the AI value (blurred sample cards) instead of a bare paywall.
private struct InsightsPremiumGate: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                lockBanner

                InsightPreviewCard(
                    title: "Best focus window",
                    value: "9:30 AM – 11:00 AM",
                    subtitle: "Usually your most productive time.",
                    chart: AnyView(LinePreview())
                )
                InsightPreviewCard(
                    title: "Pattern detected",
                    value: "Errands are often delayed after 6 PM.",
                    subtitle: nil,
                    chart: AnyView(BarsPreview())
                )
                InsightPreviewCard(
                    title: "Schedule balance",
                    value: "3.5 hrs open focus time this week",
                    subtitle: nil,
                    chart: AnyView(RingPreview(value: 0.45))
                )
                InsightPreviewCard(
                    title: "Routine consistency",
                    value: "Good",
                    subtitle: "92% consistency this week",
                    chart: AnyView(RingPreview(value: 0.92))
                )

                Button {
                    /* paywall — StoreKit follow-up */
                } label: {
                    Text("Upgrade to Premium")
                        .font(DesignTokens.Typography.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, DesignTokens.Spacing.md)
                        .background(Capsule().fill(DesignTokens.Color.accent))
                }
                .padding(.top, DesignTokens.Spacing.sm)

                Text("See all features")
                    .font(DesignTokens.Typography.subheadline.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.accent)
                    .frame(maxWidth: .infinity, alignment: .center)
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
    }

    private var lockBanner: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Your AI Insights")
                    .font(DesignTokens.Typography.title2)
                    .foregroundColor(.white)
                Text("Unlock AI insights that detect your best focus windows, routine patterns, and schedule risks.")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(.white.opacity(0.9))
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: DesignTokens.Spacing.md)
            Image(systemName: "lock.fill").font(.title3).foregroundColor(.white)
        }
        .padding(DesignTokens.Spacing.lg)
        .background(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                .fill(DesignTokens.Color.accent)
        )
    }
}

private struct InsightPreviewCard: View {
    let title: String
    let value: String
    let subtitle: String?
    let chart: AnyView

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text(title)
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.accent)
                Text(value)
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                if let subtitle {
                    Text(subtitle)
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            }
            Spacer(minLength: 0)
            chart.frame(width: 84, height: 60)
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                .fill(DesignTokens.Color.background.opacity(0.35))  // subtle "locked" veil
                .allowsHitTesting(false)
        )
    }
}

// MARK: - Small illustrative chart previews

private struct LinePreview: View {
    var body: some View {
        GeometryReader { geo in
            let pts: [CGFloat] = [0.5, 0.35, 0.6, 0.2, 0.1, 0.3, 0.25]
            Path { p in
                for (i, v) in pts.enumerated() {
                    let x = geo.size.width * CGFloat(i) / CGFloat(pts.count - 1)
                    let y = geo.size.height * v
                    if i == 0 { p.move(to: CGPoint(x: x, y: y)) } else { p.addLine(to: CGPoint(x: x, y: y)) }
                }
            }
            .stroke(DesignTokens.Color.accent, style: StrokeStyle(lineWidth: 2, lineJoin: .round))
        }
    }
}

private struct BarsPreview: View {
    private let heights: [CGFloat] = [0.4, 0.7, 1.0, 0.55, 0.85, 0.35]
    var body: some View {
        HStack(alignment: .bottom, spacing: 4) {
            ForEach(Array(heights.enumerated()), id: \.offset) { _, h in
                RoundedRectangle(cornerRadius: 2)
                    .fill(DesignTokens.Color.accent.opacity(0.7))
                    .frame(maxWidth: .infinity)
                    .frame(height: 60 * h)
            }
        }
    }
}

private struct RingPreview: View {
    let value: CGFloat
    var body: some View {
        ZStack {
            Circle().stroke(DesignTokens.Color.accent.opacity(0.15), lineWidth: 7)
            Circle().trim(from: 0, to: value)
                .stroke(DesignTokens.Color.accent, style: StrokeStyle(lineWidth: 7, lineCap: .round))
                .rotationEffect(.degrees(-90))
        }
        .frame(width: 56, height: 56)
    }
}
