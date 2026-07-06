import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = TodayViewModel()

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.uiState {
                case .idle, .loading:
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                case .error(let msg):
                    EmptyStateView(
                        icon: "exclamationmark.circle",
                        title: "Couldn't load today",
                        message: msg
                    )
                case .loaded(let tasks):
                    if tasks.isEmpty {
                        EmptyStateView(
                            icon: "calendar.badge.plus",
                            title: "Nothing scheduled today",
                            message: "Use Capture to add tasks."
                        )
                    } else {
                        loadedBody(tasks: tasks)
                    }
                }
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Today")
            .navigationBarTitleDisplayMode(.large)
        }
        .task { await viewModel.load() }
        .onChange(of: appState.selectedTab) { _, tab in
            if tab == .today { Task { await viewModel.load() } }
        }
    }

    private func loadedBody(tasks: [TimelineTask]) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                DayProgressCard(total: tasks.count, done: viewModel.doneCount)
                    .padding(.horizontal, DesignTokens.Spacing.md)
                LazyVStack(spacing: DesignTokens.Spacing.sm) {
                    ForEach(tasks) { task in
                        TimelineCard(
                            task: task,
                            visualState: viewModel.visualState(for: task),
                            onUndo: { Task { await viewModel.unschedule(taskId: task.id) } }
                        )
                    }
                }
                .padding(.horizontal, DesignTokens.Spacing.md)
                .padding(.bottom, DesignTokens.Spacing.xl)
            }
            .padding(.top, DesignTokens.Spacing.sm)
        }
        .refreshable { await viewModel.load() }
    }
}

private struct DayProgressCard: View {
    let total: Int
    let done: Int

    private var progress: Double {
        total == 0 ? 0 : Double(done) / Double(total)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text(Date(), style: .date)
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                Spacer()
                Text("\(done) of \(total) done")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            ProgressView(value: progress)
                .tint(DesignTokens.Color.accent)
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}
