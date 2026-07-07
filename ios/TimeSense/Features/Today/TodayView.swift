import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = TodayViewModel()

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.uiState {
                case .idle, .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                case .error(let msg):
                    EmptyStateView(icon: "exclamationmark.circle", title: "Couldn't load today", message: msg)
                case .loaded(let tasks):
                    loadedBody(tasks: tasks)
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
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                DateSummaryRow(total: tasks.count, done: viewModel.doneCount)

                if let best = viewModel.recommendation?.bestTask {
                    sectionHeader("AI Recommended Now")
                    AIRecommendedCard(
                        task: best,
                        load: { await viewModel.fetchExplanation(taskId: best.id) }
                    )
                }

                sectionHeader("Smart Plan")
                if tasks.isEmpty {
                    Text("Your day is open. Capture a task and TimeSense will plan it in.")
                        .font(DesignTokens.Typography.subheadline)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(DesignTokens.Spacing.lg)
                        .cardStyle()
                } else {
                    SmartPlanCard(
                        tasks: tasks,
                        onToggle: { id in Task { await viewModel.markDone(taskId: id) } },
                        onDelete: { id in Task { await viewModel.deleteTask(taskId: id) } }
                    )
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .refreshable { await viewModel.load() }
    }

    private func sectionHeader(_ text: String) -> some View {
        Text(text)
            .font(DesignTokens.Typography.headline)
            .foregroundColor(DesignTokens.Color.accent)
            .padding(.horizontal, DesignTokens.Spacing.xs)
    }
}

private struct DateSummaryRow: View {
    let total: Int
    let done: Int

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Text(Date(), format: .dateTime.month(.wide).day().year())
                .font(DesignTokens.Typography.title2)
                .foregroundColor(DesignTokens.Color.textPrimary)
            Spacer()
            Text("\(done) of \(total) complete")
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
            Image(systemName: "calendar")
                .foregroundColor(DesignTokens.Color.accent)
        }
    }
}

private struct AIRecommendedCard: View {
    let task: NowTask
    let load: () async -> RecommendationExplanation?

    var body: some View {
        let style = taskCategoryStyle(for: task.title)
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
            HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
                RoundedRectangle(cornerRadius: DesignTokens.Radius.md, style: .continuous)
                    .fill(style.color.opacity(0.16))
                    .frame(width: 56, height: 56)
                    .overlay(Image(systemName: style.icon).font(.title2).foregroundColor(style.color))
                VStack(alignment: .leading, spacing: 2) {
                    Text(task.title)
                        .font(DesignTokens.Typography.title2)
                        .foregroundColor(DesignTokens.Color.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                    if let due = task.dueAt {
                        Text("before \(due.formatted(date: .omitted, time: .shortened))")
                            .font(DesignTokens.Typography.title2.weight(.regular))
                            .foregroundColor(DesignTokens.Color.textPrimary)
                    }
                }
                Spacer(minLength: 0)
            }

            Text(metaLine(style))
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
                .frame(maxWidth: .infinity, alignment: .center)

            Divider()
            WhyThis(load: load)
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }

    private func metaLine(_ style: TaskCategoryStyle) -> String {
        var parts = [style.descriptor]
        if let m = task.estimatedMinutes { parts.append("\(m) min") }
        if style.locationAware { parts.append("Location-aware") }
        return parts.joined(separator: "  ·  ")
    }
}

private struct SmartPlanCard: View {
    let tasks: [TimelineTask]
    let onToggle: (String) -> Void
    let onDelete: (String) -> Void

    private var groups: [(name: String, tasks: [TimelineTask])] {
        let order = ["Morning", "Afternoon", "Evening", "Anytime"]
        var buckets: [String: [TimelineTask]] = [:]
        for t in tasks { buckets[bucket(for: t), default: []].append(t) }
        return order.compactMap { name in
            guard let ts = buckets[name], !ts.isEmpty else { return nil }
            let sorted = ts.sorted { ($0.scheduledStart ?? .distantFuture) < ($1.scheduledStart ?? .distantFuture) }
            return (name, sorted)
        }
    }

    private func bucket(for t: TimelineTask) -> String {
        guard let start = t.scheduledStart else { return "Anytime" }
        let hour = Calendar.current.component(.hour, from: start)
        if hour < 12 { return "Morning" }
        if hour < 17 { return "Afternoon" }
        return "Evening"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            ForEach(Array(groups.enumerated()), id: \.element.name) { idx, group in
                HStack(spacing: DesignTokens.Spacing.sm) {
                    Text(group.name)
                        .font(DesignTokens.Typography.headline)
                        .foregroundColor(DesignTokens.Color.textPrimary)
                    if idx > 0 {
                        Rectangle()
                            .fill(DesignTokens.Color.textSecondary.opacity(0.2))
                            .frame(height: 1)
                    }
                }
                .padding(.top, idx > 0 ? DesignTokens.Spacing.sm : 0)

                VStack(spacing: DesignTokens.Spacing.md) {
                    ForEach(group.tasks) { task in
                        SwipeableRow(
                            onDone: task.status == "done" ? nil : { onToggle(task.id) },
                            onDelete: { onDelete(task.id) }
                        ) {
                            SmartPlanRow(task: task, onToggle: { onToggle(task.id) })
                        }
                    }
                }
            }
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }
}

/// Swipe left to reveal Done + Delete buttons (Mail-style). Used because the Smart Plan is a custom
/// card, not a List (so `.swipeActions` isn't available).
private struct SwipeableRow<Content: View>: View {
    let onDone: (() -> Void)?
    let onDelete: () -> Void
    @ViewBuilder var content: () -> Content

    @State private var offset: CGFloat = 0
    @State private var startOffset: CGFloat = 0
    @State private var isDragging = false

    private let buttonWidth: CGFloat = 78
    private var revealWidth: CGFloat { buttonWidth * (onDone == nil ? 1 : 2) }

    var body: some View {
        ZStack(alignment: .trailing) {
            HStack(spacing: 0) {
                if let onDone {
                    actionButton("Done", "checkmark", .green) { close(); onDone() }
                }
                actionButton("Delete", "trash", DesignTokens.Color.destructive) { close(); onDelete() }
            }
            .frame(maxHeight: .infinity)

            content()
                .padding(.vertical, DesignTokens.Spacing.xs)
                .background(DesignTokens.Color.surface)
                .offset(x: offset)
                .highPriorityGesture(
                    DragGesture(minimumDistance: 14)
                        .onChanged { value in
                            guard abs(value.translation.width) > abs(value.translation.height) else { return }
                            if !isDragging { startOffset = offset; isDragging = true }
                            offset = min(0, max(startOffset + value.translation.width, -revealWidth))
                        }
                        .onEnded { value in
                            isDragging = false
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                                offset = offset < -revealWidth / 2 ? -revealWidth : 0
                            }
                        }
                )
        }
        .clipped()
    }

    private func close() {
        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) { offset = 0 }
    }

    private func actionButton(_ title: String, _ icon: String, _ color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icon).font(.body.weight(.semibold))
                Text(title).font(.caption2.weight(.semibold))
            }
            .foregroundColor(.white)
            .frame(width: buttonWidth)
            .frame(maxHeight: .infinity)
            .background(color)
        }
        .buttonStyle(.plain)
    }
}

private struct SmartPlanRow: View {
    let task: TimelineTask
    let onToggle: () -> Void

    var body: some View {
        let style = taskCategoryStyle(for: task.title)
        let done = task.status == "done"
        HStack(spacing: DesignTokens.Spacing.md) {
            Button(action: onToggle) {
                ZStack {
                    Circle().fill(style.color.opacity(0.16)).frame(width: 40, height: 40)
                    Image(systemName: done ? "checkmark" : style.icon)
                        .font(.footnote.weight(.semibold))
                        .foregroundColor(style.color)
                }
            }
            .buttonStyle(.plain)
            VStack(alignment: .leading, spacing: 2) {
                Text(task.title)
                    .font(DesignTokens.Typography.callout.weight(.semibold))
                    .foregroundColor(done ? DesignTokens.Color.textSecondary : DesignTokens.Color.textPrimary)
                    .strikethrough(done)
                    .lineLimit(1)
                Text(timeLine)
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            Spacer(minLength: 0)
        }
    }

    private var timeLine: String {
        guard let start = task.scheduledStart else {
            if let m = task.estimatedMinutes { return "Anytime  ·  \(m) min" }
            return "Anytime"
        }
        let t = start.formatted(date: .omitted, time: .shortened)
        if let m = task.estimatedMinutes { return "\(t)  ·  \(m) min" }
        return "\(t) onwards"
    }
}
