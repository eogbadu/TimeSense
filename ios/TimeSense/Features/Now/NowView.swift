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
        // "How long did that take?" — shown only while TimeSense is still learning this kind of
        // task, so it fades away once estimates are confident (never becomes a chore).
        .confirmationDialog(
            "How long did that take?",
            isPresented: Binding(
                get: { viewModel.durationPrompt != nil },
                set: { if !$0 { viewModel.durationPrompt = nil } }
            ),
            titleVisibility: .visible,
            presenting: viewModel.durationPrompt
        ) { prompt in
            Button("~15 min") { Task { await viewModel.submitDuration(taskId: prompt.id, minutes: 15) } }
            Button("~30 min") { Task { await viewModel.submitDuration(taskId: prompt.id, minutes: 30) } }
            Button("~1 hour") { Task { await viewModel.submitDuration(taskId: prompt.id, minutes: 60) } }
            Button("Skip", role: .cancel) { viewModel.durationPrompt = nil }
        } message: { _ in
            Text("This helps TimeSense learn your pace.")
        }
    }

    private func loadedBody(ctx: NowContext) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                GreetingHeader(greeting: ctx.greeting, usableMinutes: ctx.usableMinutes)
                    .padding(.top, DesignTokens.Spacing.sm)

                if let moment = ctx.moment, !moment.isEmpty {
                    MomentCard(text: moment)
                }

                if let task = ctx.bestTask {
                    BestTaskCard(
                        task: task,
                        loadWhy: { await viewModel.fetchWhy(taskId: task.id) },
                        onDone: { Task { await viewModel.markDone(taskId: task.id, title: task.title) } },
                        onSnooze: { Task { await viewModel.snooze(taskId: task.id) } },
                        onNotNow: { Task { await viewModel.notNow(taskId: task.id) } }
                    )

                    if let feasibility = ctx.feasibility, !feasibility.fits {
                        FeasibilityCard(message: feasibility.message)
                    }

                    let alts = ctx.alternatives ?? []
                    if !alts.isEmpty {
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                            Text("Or consider")
                                .sectionHeaderStyle()
                                .padding(.horizontal, DesignTokens.Spacing.xs)
                            ForEach(alts) { alt in
                                AlternativeRow(task: alt) {
                                    Task { await viewModel.markDone(taskId: alt.id, title: alt.title) }
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

/// A gentle heads-up when the best task can't be finished before it's due — with the next slot.
private struct FeasibilityCard: View {
    let message: String

    var body: some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.callout)
                .foregroundColor(DesignTokens.Color.destructive)
            Text(message)
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(DesignTokens.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous)
                .fill(DesignTokens.Color.destructive.opacity(0.10))
        )
    }
}

/// A calm, local-time-aware nudge (e.g. a gentle wind-down when it's late and nothing is urgent).
private struct MomentCard: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
            Image(systemName: "moon.stars.fill")
                .font(.title3)
                .foregroundColor(DesignTokens.Color.accent)
            Text(text)
                .font(DesignTokens.Typography.callout)
                .foregroundColor(DesignTokens.Color.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }
}

private struct BestTaskCard: View {
    let task: NowTask
    let loadWhy: () async -> String?
    let onDone: () -> Void
    let onSnooze: () -> Void
    let onNotNow: () -> Void

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

            WhyThis(load: loadWhy)

            QuickActionRow(onDone: onDone, onSnooze: onSnooze, onNotNow: onNotNow)
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }
}

/// "Why this?" — hidden by default; fetches the recommendation reason lazily on first tap so the
/// Now screen stays instant and we only spend an LLM call when the user actually asks.
private struct WhyThis: View {
    let load: () async -> String?

    @State private var isExpanded = false
    @State private var reason: String?
    @State private var loading = false

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Button(action: toggle) {
                HStack(spacing: DesignTokens.Spacing.xs) {
                    Image(systemName: "sparkles")
                    Text("Why This Recommendation?")
                    Image(systemName: "chevron.down")
                        .font(.caption2.weight(.semibold))
                        .rotationEffect(.degrees(isExpanded ? 180 : 0))
                }
                .font(DesignTokens.Typography.footnote.weight(.semibold))
                .foregroundColor(DesignTokens.Color.accent)
            }
            if isExpanded {
                Group {
                    if loading {
                        HStack(spacing: DesignTokens.Spacing.xs) {
                            ProgressView().controlSize(.small)
                            Text("Thinking…")
                                .font(DesignTokens.Typography.subheadline)
                                .foregroundColor(DesignTokens.Color.textSecondary)
                        }
                    } else if let reason {
                        Text(reason)
                            .font(DesignTokens.Typography.subheadline)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .transition(.opacity)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func toggle() {
        withAnimation(DesignTokens.Animation.fast) { isExpanded.toggle() }
        guard isExpanded, reason == nil, !loading else { return }
        loading = true
        Task {
            let result = await load()
            await MainActor.run {
                reason = result ?? "It's your best next step right now."
                loading = false
            }
        }
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
