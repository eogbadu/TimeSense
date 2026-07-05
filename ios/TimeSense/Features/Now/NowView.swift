import SwiftUI

struct NowView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = NowViewModel()

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.uiState {
                case .idle, .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                case .error(let msg):
                    EmptyStateView(icon: "exclamationmark.circle", title: "Couldn't load", message: msg)
                case .loaded(let ctx):
                    loadedBody(ctx: ctx)
                }
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Now")
            .navigationBarTitleDisplayMode(.large)
        }
        .task { await viewModel.load() }
        // Tab views stay mounted, so reload whenever the user returns to the Now tab (e.g. after
        // capturing a task) — .task alone doesn't re-run on tab switches.
        .onChange(of: appState.selectedTab) { _, tab in
            if tab == .now { Task { await viewModel.load() } }
        }
    }

    private func loadedBody(ctx: NowContext) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                GreetingHeader(greeting: ctx.greeting, usableMinutes: ctx.usableMinutes)
                    .padding(.top, DesignTokens.Spacing.sm)
                if let task = ctx.bestTask {
                    BestTaskCard(
                        task: task,
                        reason: ctx.reason,
                        onDone: { Task { await viewModel.markDone(taskId: task.id) } },
                        onSnooze: { Task { await viewModel.snooze(taskId: task.id) } },
                        onNotNow: { Task { await viewModel.notNow(taskId: task.id) } }
                    )

                    let alts = ctx.alternatives ?? []
                    if !alts.isEmpty {
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                            Text("Or consider")
                                .sectionHeaderStyle()
                                .padding(.horizontal, DesignTokens.Spacing.xs)
                            ForEach(alts) { alt in
                                AlternativeRow(task: alt) {
                                    Task { await viewModel.markDone(taskId: alt.id) }
                                }
                            }
                        }
                        .padding(.top, DesignTokens.Spacing.sm)
                    }
                } else {
                    EmptyStateView(
                        icon: "sparkles",
                        title: "You're all caught up",
                        message: "Nothing needs you right now. Capture a task and TimeSense will tell you what to do next."
                    )
                    .padding(.top, DesignTokens.Spacing.xl)
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .refreshable { await viewModel.load() }
    }
}

private struct GreetingHeader: View {
    let greeting: String
    let usableMinutes: Int

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text(greeting)
                .font(DesignTokens.Typography.largeTitle)
                .tracking(DesignTokens.Tracking.tight)
                .foregroundColor(DesignTokens.Color.textPrimary)
            HStack(spacing: DesignTokens.Spacing.xs) {
                Image(systemName: "clock")
                    .font(.footnote)
                    .foregroundColor(DesignTokens.Color.accent)
                Text("\(usableMinutes) usable minutes today")
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct BestTaskCard: View {
    let task: NowTask
    let reason: String?
    let onDone: () -> Void
    let onSnooze: () -> Void
    let onNotNow: () -> Void

    @State private var showWhy = false

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
            HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    Text("Do this next")
                        .sectionHeaderStyle()
                    Text(task.title)
                        .font(DesignTokens.Typography.title2)
                        .foregroundColor(DesignTokens.Color.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                    if let mins = task.estimatedMinutes {
                        Label("\(mins) min", systemImage: "timer")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                    }
                }
                Spacer(minLength: 0)
                PriorityBadge(priority: task.priority)
            }

            if let reason, !reason.isEmpty {
                WhyThis(reason: reason, isExpanded: $showWhy)
            }

            QuickActionRow(onDone: onDone, onSnooze: onSnooze, onNotNow: onNotNow)
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }
}

/// "Why this?" — hidden by default, reveals the recommendation reason on tap (per premium-UX spec).
private struct WhyThis: View {
    let reason: String
    @Binding var isExpanded: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Button {
                withAnimation(DesignTokens.Animation.fast) { isExpanded.toggle() }
            } label: {
                HStack(spacing: DesignTokens.Spacing.xs) {
                    Image(systemName: "sparkles")
                    Text("Why this?")
                    Image(systemName: "chevron.down")
                        .font(.caption2.weight(.semibold))
                        .rotationEffect(.degrees(isExpanded ? 180 : 0))
                }
                .font(DesignTokens.Typography.footnote.weight(.semibold))
                .foregroundColor(DesignTokens.Color.accent)
            }
            if isExpanded {
                Text(reason)
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// Compact runner-up task shown under the hero ("Or consider"); tap the circle to mark it done.
private struct AlternativeRow: View {
    let task: NowTask
    let onDone: () -> Void

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            Button(action: onDone) {
                Image(systemName: "circle")
                    .font(.title3)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            .buttonStyle(.plain)
            VStack(alignment: .leading, spacing: 2) {
                Text(task.title)
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(1)
                if let mins = task.estimatedMinutes {
                    Text("\(mins) min")
                        .font(DesignTokens.Typography.caption)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            }
            Spacer(minLength: 0)
            PriorityBadge(priority: task.priority)
        }
        .padding(.horizontal, DesignTokens.Spacing.md)
        .padding(.vertical, DesignTokens.Spacing.md)
        .cardStyle()
    }
}

private struct QuickActionRow: View {
    let onDone: () -> Void
    let onSnooze: () -> Void
    let onNotNow: () -> Void

    var body: some View {
        // Full-width primary Done + two compact secondary actions; labels never wrap.
        HStack(spacing: DesignTokens.Spacing.sm) {
            Button(action: onDone) {
                Label("Done", systemImage: "checkmark.circle.fill")
                    .font(DesignTokens.Typography.subheadline.weight(.semibold))
                    .lineLimit(1)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignTokens.Spacing.sm)
                    .background(DesignTokens.Color.accent)
                    .clipShape(Capsule())
            }
            SecondaryAction(title: "Snooze", systemImage: "clock.arrow.2.circlepath", action: onSnooze)
            SecondaryAction(title: "Not now", systemImage: "xmark", action: onNotNow)
        }
    }
}

private struct SecondaryAction: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .labelStyle(.titleAndIcon)
                .font(DesignTokens.Typography.footnote.weight(.medium))
                .lineLimit(1)
                .fixedSize()
                .foregroundColor(DesignTokens.Color.textSecondary)
                .padding(.horizontal, DesignTokens.Spacing.sm)
                .padding(.vertical, DesignTokens.Spacing.sm)
                .background(
                    Capsule().stroke(DesignTokens.Color.textSecondary.opacity(0.25), lineWidth: 1)
                )
        }
    }
}

private struct PriorityBadge: View {
    let priority: Int
    private var label: String {
        switch priority {
        case 1: return "P1"
        case 2: return "P2"
        case 3: return "P3"
        case 4: return "P4"
        default: return "P5"
        }
    }
    private var color: Color {
        switch priority {
        case 1: return .red
        case 2: return .orange
        default: return DesignTokens.Color.textSecondary
        }
    }
    var body: some View {
        Text(label)
            .font(DesignTokens.Typography.caption.weight(.bold))
            .foregroundColor(color)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.12))
            .cornerRadius(DesignTokens.Radius.sm)
    }
}
