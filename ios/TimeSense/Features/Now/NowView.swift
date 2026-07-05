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
                    BestTaskCard(task: task, onDone: {
                        Task { await viewModel.markDone(taskId: task.id) }
                    })
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
    let onDone: () -> Void

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
            QuickActionRow(onDone: onDone)
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }
}

private struct QuickActionRow: View {
    let onDone: () -> Void

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Button(action: onDone) {
                Label("Done", systemImage: "checkmark.circle.fill")
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, DesignTokens.Spacing.md)
                    .padding(.vertical, DesignTokens.Spacing.xs)
                    .background(DesignTokens.Color.accent)
                    .cornerRadius(DesignTokens.Radius.pill)
            }
            Button(action: {}) {
                Label("Snooze", systemImage: "clock.arrow.2.circlepath")
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .padding(.horizontal, DesignTokens.Spacing.md)
                    .padding(.vertical, DesignTokens.Spacing.xs)
                    .background(DesignTokens.Color.surface)
                    .cornerRadius(DesignTokens.Radius.pill)
                    .overlay(RoundedRectangle(cornerRadius: DesignTokens.Radius.pill).stroke(DesignTokens.Color.textSecondary.opacity(0.3), lineWidth: 1))
            }
            Button(action: {}) {
                Label("Not now", systemImage: "xmark.circle")
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .padding(.horizontal, DesignTokens.Spacing.md)
                    .padding(.vertical, DesignTokens.Spacing.xs)
            }
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
