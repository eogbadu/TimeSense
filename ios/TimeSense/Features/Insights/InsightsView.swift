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
        .task(id: appState.isPremium) {
            // Re-runs when entitlement resolves, so Insights loads as soon as Premium is known.
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
        VStack(spacing: DesignTokens.Spacing.md) {
            StatRow(icon: "checkmark.circle.fill", tint: Cosmic.green, label: "Tasks completed",
                    value: "\(insight.tasksCompleted) of \(insight.tasksTotal)")
            StatRow(icon: "percent", tint: Cosmic.blue, label: "Completion rate", value: completionRateText)
            if let meal = insight.mostSkippedMeal {
                StatRow(icon: "fork.knife", tint: Cosmic.amber, label: "Most skipped meal", value: meal.capitalized)
            }
            if insight.lateWakeCount > 0 {
                StatRow(icon: "moon.zzz.fill", tint: Cosmic.violet, label: "Late wake-ups", value: "\(insight.lateWakeCount)")
            }
            if insight.commuteConfirmedCount > 0 {
                StatRow(icon: "car.fill", tint: Cosmic.cyan, label: "Commutes tracked", value: "\(insight.commuteConfirmedCount)")
            }
            if let rate = insight.recommendationAcceptanceRate {
                StatRow(icon: "sparkles", tint: Cosmic.blue, label: "Recommendations accepted",
                        value: "\(Int((rate * 100).rounded()))%",
                        detail: "\(insight.recommendationsAccepted) of \(insight.recommendationsShown) shown")
            }
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}

private struct StatRow: View {
    let icon: String
    var tint: Color = DesignTokens.Color.accent
    let label: String
    let value: String
    var detail: String? = nil

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous)
                .fill(tint.opacity(0.16))
                .frame(width: 32, height: 32)
                .overlay(Image(systemName: icon).font(.footnote.weight(.semibold)).foregroundColor(tint))
            Text(label)
                .font(DesignTokens.Typography.callout)
                .foregroundColor(DesignTokens.Color.textPrimary)
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(value)
                    .font(DesignTokens.Typography.callout.weight(.bold))
                    .foregroundColor(DesignTokens.Color.textPrimary)
                if let detail {
                    Text(detail)
                        .font(DesignTokens.Typography.caption)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            }
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
                    title: "Best focus window", value: "9:30 AM – 11:00 AM",
                    subtitle: "Usually your most productive time.", tint: Cosmic.blue,
                    chart: AnyView(LinePreview(color: Cosmic.blue))
                )
                InsightPreviewCard(
                    title: "Pattern detected", value: "Errands are often delayed after 6 PM.",
                    subtitle: nil, tint: Cosmic.amber,
                    chart: AnyView(BarsPreview(color: Cosmic.amber))
                )
                InsightPreviewCard(
                    title: "Schedule balance", value: "3.5 hrs open focus time this week",
                    subtitle: nil, tint: Cosmic.green,
                    chart: AnyView(RingPreview(value: 0.45, color: Cosmic.green))
                )
                InsightPreviewCard(
                    title: "Routine consistency", value: "Good",
                    subtitle: "92% consistency this week", tint: Cosmic.violet,
                    chart: AnyView(RingPreview(value: 0.92, color: Cosmic.violet))
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
            Image(systemName: "lock.fill").font(.subheadline).foregroundColor(.white)
                .padding(10)
                .background(Circle().fill(Color.white.opacity(0.18)))
        }
        .padding(DesignTokens.Spacing.lg)
        .background(
            LinearGradient(colors: [Cosmic.blue, Cosmic.violet],
                           startPoint: .topLeading, endPoint: .bottomTrailing)
        )
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous))
        .shadow(color: Cosmic.violet.opacity(0.3), radius: 20, y: 10)
    }
}

private struct InsightPreviewCard: View {
    let title: String
    let value: String
    let subtitle: String?
    var tint: Color = DesignTokens.Color.accent
    let chart: AnyView

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text(title)
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
                    .foregroundColor(tint)
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
    var color: Color = DesignTokens.Color.accent
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
            .stroke(color, style: StrokeStyle(lineWidth: 2.5, lineJoin: .round))
            .shadow(color: color.opacity(0.6), radius: 4)
        }
    }
}

private struct BarsPreview: View {
    var color: Color = DesignTokens.Color.accent
    private let heights: [CGFloat] = [0.4, 0.7, 1.0, 0.55, 0.85, 0.35]
    var body: some View {
        HStack(alignment: .bottom, spacing: 4) {
            ForEach(Array(heights.enumerated()), id: \.offset) { _, h in
                RoundedRectangle(cornerRadius: 2)
                    .fill(LinearGradient(colors: [color, color.opacity(0.45)],
                                         startPoint: .top, endPoint: .bottom))
                    .frame(maxWidth: .infinity)
                    .frame(height: 60 * h)
            }
        }
    }
}

private struct RingPreview: View {
    let value: CGFloat
    var color: Color = DesignTokens.Color.accent
    var body: some View {
        ZStack {
            Circle().stroke(color.opacity(0.16), lineWidth: 7)
            Circle().trim(from: 0, to: value)
                .stroke(color, style: StrokeStyle(lineWidth: 7, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .shadow(color: color.opacity(0.5), radius: 4)
        }
        .frame(width: 56, height: 56)
    }
}
