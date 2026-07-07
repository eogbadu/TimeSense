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
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Image(systemName: "sparkles").foregroundColor(DesignTokens.Color.accent)
                }
            }
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
                AnalysisBanner(lastLoaded: viewModel.lastLoaded)
                ContextChipsRow()

                if let moment = ctx.moment, !moment.isEmpty {
                    MomentCard(text: moment)
                }

                if let task = ctx.bestTask {
                    BestNextActionCard(
                        task: task,
                        confidence: ctx.confidence,
                        loadExplanation: { await viewModel.fetchExplanation(taskId: task.id) },
                        onDone: { Task { await viewModel.markDone(taskId: task.id, title: task.title) } },
                        onSnooze: { Task { await viewModel.snooze(taskId: task.id) } },
                        onNotNow: { Task { await viewModel.notNow(taskId: task.id) } }
                    )

                    if let feasibility = ctx.feasibility, !feasibility.fits {
                        FeasibilityCard(message: feasibility.message)
                    }

                    let alts = ctx.alternatives ?? []
                    if !alts.isEmpty {
                        OtherOptionsSection(
                            alternatives: alts,
                            loadExplanation: { id in await viewModel.fetchExplanation(taskId: id) }
                        )
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
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .refreshable { await viewModel.load() }
    }
}

/// "TimeSense analyzed your day · Re-evaluated N min ago" — reassures the user the pick is fresh.
private struct AnalysisBanner: View {
    let lastLoaded: Date?

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: "arrow.triangle.2.circlepath")
                .font(.title3.weight(.semibold))
                .foregroundColor(DesignTokens.Color.accent)
            VStack(alignment: .leading, spacing: 2) {
                Text("TimeSense analyzed your day")
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                Text(reevaluated)
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            Spacer(minLength: 0)
        }
        .padding(DesignTokens.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                .fill(DesignTokens.Color.accent.opacity(0.10))
        )
    }

    private var reevaluated: String {
        guard let lastLoaded else { return "Just now" }
        let mins = Int(Date().timeIntervalSince(lastLoaded) / 60)
        if mins <= 0 { return "Re-evaluated just now" }
        if mins == 1 { return "Re-evaluated 1 min ago" }
        return "Re-evaluated \(mins) min ago"
    }
}

/// The signal categories TimeSense weighs — all five fit on screen at once (no scrolling); each
/// chip takes an equal share of the row.
private struct ContextChipsRow: View {
    private let chips = ["Calendar", "Routine", "Location", "Time", "Tasks"]

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.xs) {
            ForEach(chips, id: \.self) { chip in
                Text(chip)
                    .font(DesignTokens.Typography.caption.weight(.medium))
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignTokens.Spacing.sm)
                    .background(Capsule().fill(DesignTokens.Color.surface))
                    .overlay(Capsule().stroke(DesignTokens.Color.textSecondary.opacity(0.18), lineWidth: 1))
            }
        }
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

private struct BestNextActionCard: View {
    let task: NowTask
    let confidence: Double?
    let loadExplanation: () async -> RecommendationExplanation?
    let onDone: () -> Void
    let onSnooze: () -> Void
    let onNotNow: () -> Void

    var body: some View {
        let style = taskCategoryStyle(for: task.title)
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
            HStack {
                Text("Best Next Action")
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                Spacer()
                Text("AI Recommended")
                    .font(DesignTokens.Typography.caption.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.accent)
                    .padding(.horizontal, DesignTokens.Spacing.sm)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(DesignTokens.Color.accent.opacity(0.12)))
            }

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
                    if let mins = task.estimatedMinutes {
                        Text("for \(mins) minutes")
                            .font(DesignTokens.Typography.title2.weight(.regular))
                            .foregroundColor(DesignTokens.Color.textPrimary)
                    }
                }
                Spacer(minLength: 0)
            }

            Text(metaLine(style: style))
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
                .frame(maxWidth: .infinity, alignment: .center)

            if let confidence {
                HStack(spacing: DesignTokens.Spacing.md) {
                    Text("Confidence")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                    ProgressView(value: confidence).tint(DesignTokens.Color.accent)
                    Text("\(Int((confidence * 100).rounded()))%")
                        .font(DesignTokens.Typography.footnote.weight(.bold))
                        .foregroundColor(DesignTokens.Color.textPrimary)
                        .monospacedDigit()
                }
            }

            Divider()
            WhyThis(load: loadExplanation)
            QuickActionRow(onDone: onDone, onSnooze: onSnooze, onNotNow: onNotNow)
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }

    private func metaLine(style: TaskCategoryStyle) -> String {
        var parts = [priorityLabel(task.priority) + " priority", style.descriptor]
        if let m = task.estimatedMinutes { parts.append("\(m) min") }
        return parts.joined(separator: "  ·  ")
    }
}

private func priorityLabel(_ p: Int) -> String {
    p <= 2 ? "High" : (p == 3 ? "Medium" : "Low")
}

// MARK: - Client-side task styling (icon/colour/descriptor from the title)

struct TaskCategoryStyle {
    let icon: String
    let color: Color
    let descriptor: String
    var locationAware: Bool = false
}

func taskCategoryStyle(for title: String) -> TaskCategoryStyle {
    let t = " \(title.lowercased()) "
    func has(_ words: [String]) -> Bool { words.contains { t.contains($0) } }
    if has(["revise", "paper", "write", "draft", "essay", "report", "document", "proposal", "read", "study", "research"]) {
        return TaskCategoryStyle(icon: "doc.text.fill", color: DesignTokens.Color.accent, descriptor: "Focus task")
    }
    if has(["jira", "ticket", "review", "code", "bug", "pr ", "pull request"]) {
        return TaskCategoryStyle(icon: "checklist", color: .orange, descriptor: "Focus task")
    }
    if has(["email", "reply", "respond", "inbox", "message", "slack"]) {
        return TaskCategoryStyle(icon: "envelope.fill", color: .blue, descriptor: "Low focus")
    }
    if has(["walk", "run", "gym", "exercise", "workout", "stretch", "yoga", "break"]) {
        return TaskCategoryStyle(icon: "figure.walk", color: .orange, descriptor: "Health break")
    }
    if has(["call", "phone", "dial"]) {
        return TaskCategoryStyle(icon: "phone.fill", color: .green, descriptor: "Quick task")
    }
    if has(["buy", "shop", "store", "groceries", "grocery", "home depot", "mall", "walmart", "target", "market", "errand", "gift"]) {
        return TaskCategoryStyle(icon: "cart.fill", color: .orange, descriptor: "Errand", locationAware: true)
    }
    if has(["clean", "laundry", "dishes", "tidy", "vacuum", "organize"]) {
        return TaskCategoryStyle(icon: "sparkles", color: .teal, descriptor: "Chore")
    }
    if has(["meeting", "standup", "sync", "1:1"]) {
        return TaskCategoryStyle(icon: "person.2.fill", color: .purple, descriptor: "Meeting")
    }
    if has(["doctor", "dentist", "appointment", "chiropractor"]) {
        return TaskCategoryStyle(icon: "cross.case.fill", color: .pink, descriptor: "Appointment", locationAware: true)
    }
    if has(["family", "kids", "wife", "husband", "date night"]) {
        return TaskCategoryStyle(icon: "house.fill", color: .blue, descriptor: "Personal")
    }
    return TaskCategoryStyle(icon: "checkmark.circle.fill", color: DesignTokens.Color.accent, descriptor: "Task")
}

/// "Why This Recommendation?" — fetches the structured explanation lazily on tap (so Now stays
/// instant and we only spend an LLM call when asked), then presents it as a sheet.
struct WhyThis: View {
    let load: () async -> RecommendationExplanation?

    @State private var loading = false
    @State private var explanation: RecommendationExplanation?
    @State private var showSheet = false

    var body: some View {
        Button {
            guard !loading else { return }
            loading = true
            Task {
                let result = await load()
                await MainActor.run {
                    explanation = result
                    loading = false
                    showSheet = result != nil
                }
            }
        } label: {
            HStack(spacing: DesignTokens.Spacing.xs) {
                Image(systemName: "sparkles")
                Text("Why This Recommendation?")
                if loading {
                    ProgressView().controlSize(.small)
                } else {
                    Image(systemName: "chevron.right").font(.caption2.weight(.semibold))
                }
            }
            .font(DesignTokens.Typography.footnote.weight(.semibold))
            .foregroundColor(DesignTokens.Color.accent)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .sheet(isPresented: $showSheet) {
            if let explanation {
                RecommendationExplanationSheet(explanation: explanation)
            }
        }
    }
}

struct RecommendationExplanationSheet: View {
    let explanation: RecommendationExplanation
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("Recommended action") {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(explanation.recommendedAction.title)
                            .font(DesignTokens.Typography.headline)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        if let m = explanation.recommendedAction.recommendedDurationMinutes {
                            Text("about \(m) minutes")
                                .font(DesignTokens.Typography.footnote)
                                .foregroundColor(DesignTokens.Color.textSecondary)
                        }
                    }
                }
                Section("Confidence") {
                    HStack(spacing: DesignTokens.Spacing.md) {
                        Text("\(Int((explanation.confidence * 100).rounded()))%")
                            .font(DesignTokens.Typography.title2)
                            .foregroundColor(DesignTokens.Color.accent)
                        ProgressView(value: explanation.confidence)
                            .tint(DesignTokens.Color.accent)
                    }
                }
                Section("Context used") {
                    ForEach(explanation.contextUsed, id: \.self) { line in
                        Label(line, systemImage: "circle.fill")
                            .labelStyle(BulletLabelStyle())
                            .font(DesignTokens.Typography.subheadline)
                    }
                }
                Section("Decision factors") {
                    ForEach(explanation.decisionFactors) { f in
                        HStack {
                            Text(f.name).foregroundColor(DesignTokens.Color.textPrimary)
                            Spacer()
                            Text(f.rating)
                                .font(DesignTokens.Typography.footnote.weight(.semibold))
                                .foregroundColor(DesignTokens.Color.textSecondary)
                        }
                    }
                }
                if !explanation.alternativesConsidered.isEmpty {
                    Section("Other options considered") {
                        ForEach(explanation.alternativesConsidered) { a in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(a.title)
                                    .font(DesignTokens.Typography.subheadline)
                                    .foregroundColor(DesignTokens.Color.textPrimary)
                                Text(a.reasonNotSelected)
                                    .font(DesignTokens.Typography.caption)
                                    .foregroundColor(DesignTokens.Color.textSecondary)
                            }
                        }
                    }
                }
                Section("Summary") {
                    Text(explanation.summary)
                        .font(DesignTokens.Typography.subheadline)
                        .foregroundColor(DesignTokens.Color.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .navigationTitle("Why This Recommendation?")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

/// Renders a tiny bullet before the text.
struct BulletLabelStyle: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: DesignTokens.Spacing.sm) {
            Image(systemName: "circle.fill")
                .font(.system(size: 5))
                .foregroundColor(DesignTokens.Color.accent)
            configuration.title
        }
    }
}

/// "Other good options" — the runner-up tasks; tapping a row opens its explanation.
private struct OtherOptionsSection: View {
    let alternatives: [NowTask]
    let loadExplanation: (String) async -> RecommendationExplanation?

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Other good options")
                .font(DesignTokens.Typography.headline)
                .foregroundColor(DesignTokens.Color.accent)
                .padding(.horizontal, DesignTokens.Spacing.xs)

            VStack(spacing: 0) {
                ForEach(Array(alternatives.enumerated()), id: \.element.id) { idx, alt in
                    OptionRow(task: alt, load: { await loadExplanation(alt.id) })
                    if idx < alternatives.count - 1 {
                        Divider().padding(.leading, 68)
                    }
                }
            }
            .cardStyle()
        }
    }
}

private struct OptionRow: View {
    let task: NowTask
    let load: () async -> RecommendationExplanation?

    @State private var loading = false
    @State private var explanation: RecommendationExplanation?
    @State private var showSheet = false

    var body: some View {
        let style = taskCategoryStyle(for: task.title)
        Button {
            guard !loading else { return }
            loading = true
            Task {
                let result = await load()
                await MainActor.run { explanation = result; loading = false; showSheet = result != nil }
            }
        } label: {
            HStack(spacing: DesignTokens.Spacing.md) {
                RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous)
                    .fill(style.color.opacity(0.16))
                    .frame(width: 40, height: 40)
                    .overlay(Image(systemName: style.icon).foregroundColor(style.color))
                VStack(alignment: .leading, spacing: 2) {
                    Text(task.title)
                        .font(DesignTokens.Typography.callout.weight(.semibold))
                        .foregroundColor(DesignTokens.Color.textPrimary)
                        .lineLimit(1)
                    HStack(spacing: 4) {
                        Text(subtitle(style: style))
                            .font(DesignTokens.Typography.caption)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                        if style.descriptor == "Health break" || style.descriptor == "Low focus" {
                            Circle().fill(Color.green).frame(width: 5, height: 5)
                        }
                    }
                }
                Spacer(minLength: 0)
                if loading {
                    ProgressView().controlSize(.small)
                } else {
                    Image(systemName: "chevron.right")
                        .font(.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            }
            .padding(DesignTokens.Spacing.md)
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $showSheet) {
            if let explanation { RecommendationExplanationSheet(explanation: explanation) }
        }
    }

    private func subtitle(style: TaskCategoryStyle) -> String {
        if let m = task.estimatedMinutes { return "\(m) min  ·  \(style.descriptor)" }
        return style.descriptor
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

