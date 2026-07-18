import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = TodayViewModel()
    @ObservedObject private var calendar = CalendarSyncService.shared
    @ObservedObject private var router = DeepLinkRouter.shared
    @State private var scheduleDraft: ScheduleDraft?

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.uiState {
                case .idle, .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                case .error(let msg):
                    EmptyStateView(icon: "exclamationmark.circle", title: "Couldn't load today", message: msg)
                case .loaded(let entries):
                    loadedBody(entries: entries)
                }
            }
            .background(CosmicBackground())
            .navigationTitle("Today")
            .navigationBarTitleDisplayMode(.large)
            .sheet(item: $scheduleDraft) { draft in
                eventEditorSheet(for: draft)
            }
        }
        .task {
            await viewModel.load()
            await calendar.syncIfAuthorized()
        }
        .onChange(of: appState.selectedTab) { _, tab in
            if tab == .today {
                Task { await viewModel.load() }
                Task { await calendar.syncIfAuthorized() }
            }
        }
        // A tapped "block time" offer routes here → open the scheduler pre-filled for that task.
        .onChange(of: router.route) { _, route in
            if case let .scheduleTask(taskId, title) = route {
                Task {
                    router.route = nil
                    guard await calendar.ensureWriteAccess() else { return }
                    let slot = await viewModel.suggestedSlot(taskId: taskId, estimatedMinutes: nil)
                    scheduleDraft = ScheduleDraft(id: taskId, title: title, start: slot.start, end: slot.end)
                }
            }
        }
    }

    private func loadedBody(entries: [TimelineEntry]) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                DateSummaryRow(total: viewModel.tasks.count, done: viewModel.doneCount)

                if let best = viewModel.recommendation?.bestTask {
                    sectionHeader("AI Recommended Now")
                    AIRecommendedCard(
                        task: best,
                        load: { await viewModel.fetchExplanation(taskId: best.id) }
                    )
                }

                sectionHeader("Smart Plan")
                if entries.isEmpty {
                    Text("Your day is open. Capture a task and TimeSense will plan it in.")
                        .font(DesignTokens.Typography.subheadline)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(DesignTokens.Spacing.lg)
                        .cardStyle()
                } else {
                    SmartPlanCard(
                        entries: entries,
                        onToggle: { id in Task { await viewModel.markDone(taskId: id) } },
                        onDelete: { id in Task { await viewModel.deleteTask(taskId: id) } },
                        onSchedule: { task in
                            Task {
                                guard await calendar.ensureWriteAccess() else { return }
                                let slot = await viewModel.suggestedSlot(
                                    taskId: task.id, estimatedMinutes: task.estimatedMinutes
                                )
                                scheduleDraft = ScheduleDraft(
                                    id: task.id, title: task.title, start: slot.start, end: slot.end
                                )
                            }
                        }
                    )
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, 96)   // clear the custom tab bar (content can scroll under it in the pager)
        }
        .refreshable { await viewModel.load() }
    }

    /// Native "add event" editor pre-filled with the engine-suggested block, for the user to review
    /// and confirm.
    @ViewBuilder
    private func eventEditorSheet(for draft: ScheduleDraft) -> some View {
        EventEditorView(
            event: calendar.makeDraftEvent(title: draft.title, start: draft.start, end: draft.end),
            eventStore: calendar.eventStore
        ) { saved in
            scheduleDraft = nil
            if saved { Task { await calendar.syncIfAuthorized() } }
        }
        .ignoresSafeArea()
    }

    private func sectionHeader(_ text: String) -> some View {
        Text(text)
            .font(DesignTokens.Typography.headline)
            .foregroundColor(DesignTokens.Color.accent)
            .padding(.horizontal, DesignTokens.Spacing.xs)
    }
}

/// A task + the engine-suggested time block to schedule it into (drives the approval editor sheet).
private struct ScheduleDraft: Identifiable {
    let id: String
    let title: String
    let start: Date
    let end: Date
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
        let accent = heroAccent(style.descriptor)
        VStack(spacing: 0) {
            // Dark hero header with the recommendation's domain colour (matches the Now hero).
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                HStack(spacing: 6) {
                    Image(systemName: "sparkles").font(.footnote).foregroundStyle(accent)
                    Text("AI Recommended")
                        .font(DesignTokens.Typography.footnote.weight(.semibold))
                        .foregroundStyle(DesignTokens.Color.onHero.opacity(0.9))
                    Spacer(minLength: 0)
                }
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(task.title)
                            .font(DesignTokens.Typography.title.weight(.bold))
                            .foregroundStyle(DesignTokens.Color.onHero)
                            .fixedSize(horizontal: false, vertical: true)
                        if let due = task.dueAt {
                            Text("before \(due.formatted(date: .omitted, time: .shortened))")
                                .font(DesignTokens.Typography.title2.weight(.regular))
                                .foregroundStyle(DesignTokens.Color.onHero.opacity(0.82))
                        }
                    }
                    Spacer(minLength: DesignTokens.Spacing.sm)
                    HeroGlyph(systemName: style.icon, tint: accent)
                }
                HStack(spacing: DesignTokens.Spacing.sm) {
                    HeroPill(icon: style.icon, text: style.descriptor, tint: accent)
                    if let m = task.estimatedMinutes { HeroPill(icon: "clock", text: "\(m) min", tint: DesignTokens.Color.onHero.opacity(0.8)) }
                }
            }
            .padding(DesignTokens.Spacing.lg)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(HeroBackground(accent: accent))

            VStack(alignment: .leading) { WhyThis(load: load) }
                .padding(DesignTokens.Spacing.lg)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Cosmic.surface)
        }
        .heroCardChrome(glow: accent)
    }
}

private struct SmartPlanCard: View {
    let entries: [TimelineEntry]
    let onToggle: (String) -> Void
    let onDelete: (String) -> Void
    let onSchedule: (TimelineTask) -> Void

    private var groups: [(name: String, entries: [TimelineEntry])] {
        let order = ["Morning", "Afternoon", "Evening", "Anytime"]
        var buckets: [String: [TimelineEntry]] = [:]
        for e in entries { buckets[bucket(for: e), default: []].append(e) }
        return order.compactMap { name in
            guard let es = buckets[name], !es.isEmpty else { return nil }
            let sorted = es.sorted { ($0.start ?? .distantFuture) < ($1.start ?? .distantFuture) }
            return (name, sorted)
        }
    }

    private func groupColor(_ name: String) -> Color {
        // Warm → cool across the day: sunrise yellow → midday orange → dusk violet.
        switch name {
        case "Morning": return Cosmic.yellow
        case "Afternoon": return Cosmic.orange
        case "Evening": return Cosmic.violet
        default: return Cosmic.cyan   // "Anytime"
        }
    }

    private func bucket(for e: TimelineEntry) -> String {
        guard let start = e.start else { return "Anytime" }
        let hour = Calendar.current.component(.hour, from: start)
        if hour < 12 { return "Morning" }
        if hour < 17 { return "Afternoon" }
        return "Evening"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            ForEach(Array(groups.enumerated()), id: \.element.name) { idx, group in
                HStack(spacing: DesignTokens.Spacing.sm) {
                    Circle()
                        .fill(groupColor(group.name))
                        .frame(width: 8, height: 8)
                        .shadow(color: groupColor(group.name).opacity(0.7), radius: 4)
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
                    ForEach(group.entries) { entry in
                        if let task = entry.task {
                            SwipeableRow(
                                onDone: task.status == "done" ? nil : { onToggle(task.id) },
                                onDelete: { onDelete(task.id) }
                            ) {
                                SmartPlanRow(task: task, onToggle: { onToggle(task.id) })
                                    .contextMenu {
                                        Button { onSchedule(task) } label: {
                                            Label("Find a time & add to calendar", systemImage: "calendar.badge.plus")
                                        }
                                    }
                            }
                        } else {
                            // Calendar meeting: read-only busy block (no swipe/toggle/schedule).
                            CalendarBlockRow(entry: entry)
                        }
                    }
                }
            }
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }
}

/// A read-only calendar meeting woven into the Smart Plan — the plan schedules around it, but the
/// user manages it in their calendar, so there's no Done/Delete/Schedule affordance.
private struct CalendarBlockRow: View {
    let entry: TimelineEntry

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            ZStack {
                Circle().fill(DesignTokens.Color.accent.opacity(0.12)).frame(width: 40, height: 40)
                Image(systemName: "calendar")
                    .font(.footnote.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.accent)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.title)
                    .font(DesignTokens.Typography.callout.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(1)
                Text(timeLine)
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            Spacer(minLength: 0)
            Text("Calendar")
                .font(DesignTokens.Typography.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
                .padding(.horizontal, DesignTokens.Spacing.sm)
                .padding(.vertical, 2)
                .background(Capsule().fill(DesignTokens.Color.accent.opacity(0.10)))
        }
        .padding(.vertical, DesignTokens.Spacing.xs)
    }

    private var timeLine: String {
        guard let start = entry.start else { return "" }
        var line = start.formatted(date: .omitted, time: .shortened)
        if let end = entry.end {
            line += " – " + end.formatted(date: .omitted, time: .shortened)
        }
        if let loc = entry.location, !loc.isEmpty { line += "  ·  \(loc)" }
        return line
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
            .foregroundColor(DesignTokens.Color.onHero)
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
