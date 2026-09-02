import SwiftUI

struct NowView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = NowViewModel()
    /// Set once a reason is chosen — drives the "what would you rather do?" picker (TIME-295).
    @State private var swapPrompt: SwapPrompt?
    /// Observed so an overrunning timer surfaces its prompt as soon as Now is shown (TIME-299).
    @ObservedObject private var timers = TaskTimerStore.shared

    // Set when the user taps Disagree — drives the "why not this one?" reason prompt (TIME-272).
    @State private var disagreeTaskId: String?

    // Resolving a passed deadline (TIME-309). Two of the three answers need a second step: picking
    // a new date, and confirming a delete. "Mark done" doesn't — it's the same action as anywhere
    // else and reversing it is cheap.
    @State private var rescheduleTarget: AwaitingResolution?
    @State private var removeTarget: AwaitingResolution?

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
            .background(CosmicBackground())
            .navigationTitle("Now")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task { await viewModel.load() }
        // Tab views stay mounted, so reload whenever the user returns to the Now tab (e.g. after
        // capturing a task) — .task alone doesn't re-run on tab switches.
        .onChange(of: appState.selectedTab) { _, tab in
            if tab == .now { Task { await viewModel.load() } }
        }
        // "How long did that take?" — shown only while TimeSense is still learning this kind of
        // task, so it fades away once estimates are confident (never becomes a chore).
        // A sheet rather than three fixed buttons: those buttons could only ever say 15 / 30 / 60,
        // and feeding those coarse answers into the estimator is what produced the "everything
        // takes 23 minutes" bug (TIME-286/287).
        .sheet(item: $viewModel.durationPrompt) { prompt in
            DurationFeedbackSheet(
                prompt: prompt,
                onSubmit: { minutes, correctedType in
                    Task { await viewModel.submitDuration(taskId: prompt.id, minutes: minutes,
                                                          taskType: correctedType) }
                },
                onSkip: { viewModel.durationPrompt = nil }
            )
        }
        // "Why not this one?" — a light optional prompt after Disagree. Each reason (and Skip) records
        // the disagree so a different pick surfaces; the reason feeds reason-based learning (TIME-272).
        .confirmationDialog(
            "Why not this one?",
            isPresented: Binding(
                get: { disagreeTaskId != nil },
                set: { if !$0 { disagreeTaskId = nil } }
            ),
            titleVisibility: .visible,
            presenting: disagreeTaskId
        ) { taskId in
            // Each reason now opens the "what would you rather do?" picker rather than recording
            // and moving on. Saying what you'd rather do is a far stronger signal than saying no
            // (TIME-295) — but it stays optional: dismissing the picker still records the disagree.
            Button("Wrong time") { offerSwap(taskId, reason: "wrong_time") }
            Button("Not a priority") { offerSwap(taskId, reason: "not_priority") }
            Button("Not relevant") { offerSwap(taskId, reason: "not_relevant") }
            Button("Too big right now") { offerSwap(taskId, reason: "too_big") }
            Button("Just skip") { Task { await viewModel.disagree(taskId: taskId) } }
            Button("Cancel", role: .cancel) { disagreeTaskId = nil }
        } message: { _ in
            Text("Optional — helps TimeSense pick better next time.")
        }
        .sheet(item: $swapPrompt) { prompt in
            SwapPickerSheet(
                prompt: prompt,
                loadCandidates: { await viewModel.swapCandidates(excluding: prompt.rejectedTaskId) },
                onPick: { chosenId in
                    Task {
                        await viewModel.swap(rejectedTaskId: prompt.rejectedTaskId,
                                             chosenTaskId: chosenId, reason: prompt.reason)
                    }
                },
                // Backing out must not lose the disagree the user already expressed.
                onSkip: { Task { await viewModel.disagree(taskId: prompt.rejectedTaskId,
                                                          reason: prompt.reason) } }
            )
        }
        .sheet(item: $rescheduleTarget) { item in
            RescheduleSheet(
                item: item,
                onPick: { newDue in
                    Task { await viewModel.reschedule(taskId: item.task.id, to: newDue) }
                },
                onCancel: { rescheduleTarget = nil }
            )
        }
        // Deleting is the one irreversible answer, so it asks. Everything else on this card is undoable.
        .confirmationDialog(
            "Remove this task?",
            isPresented: Binding(
                get: { removeTarget != nil },
                set: { if !$0 { removeTarget = nil } }
            ),
            titleVisibility: .visible,
            presenting: removeTarget
        ) { item in
            Button("Remove", role: .destructive) {
                Task { await viewModel.removeTask(taskId: item.task.id) }
            }
            Button("Keep it", role: .cancel) { removeTarget = nil }
        } message: { item in
            Text("\"\(item.task.title)\" will be deleted. This can't be undone.")
        }
    }

    /// Record the reason and immediately ask what the user would rather do. The disagree itself is
    /// only sent if they back out of the picker, so it is recorded exactly once either way.
    private func offerSwap(_ taskId: String, reason: String) {
        swapPrompt = SwapPrompt(rejectedTaskId: taskId, reason: reason)
    }

    private func loadedBody(ctx: NowContext) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                AnalysisBanner(lastLoaded: viewModel.lastLoaded)

                // A full cross-domain engine suggestion (wind-down, prep-for-meeting, nearby errand…)
                // supersedes the simpler local wind-down nudge when available.
                if let suggestion = viewModel.suggestion, suggestion.isCrossDomainAction {
                    SuggestionCard(suggestion: suggestion)
                } else if let moment = ctx.moment, !moment.isEmpty {
                    MomentCard(text: moment)
                }

                // "Still on this?" — shown when a timer has run well past its estimate. The
                // notification may never have been seen (or permission declined), so the in-app
                // prompt is the reliable path, not a duplicate (TIME-299).
                if let running = timers.running, running.needsOverrunPrompt {
                    TimerOverrunCard(
                        timer: running,
                        onDone: {
                            Task {
                                await viewModel.markDone(taskId: running.taskId,
                                                         title: running.taskTitle,
                                                         estimatedMinutes: running.estimatedMinutes)
                            }
                        },
                        onStillGoing: { timers.acknowledgeOverrun() }
                    )
                }

                // Deadlines that have already passed. Placed ABOVE the recommendation because it
                // is the honest order: the assistant has stopped recommending these, and saying so
                // is more useful than quietly ranking them last (TIME-309).
                let stale = ctx.awaitingResolution ?? []
                if !stale.isEmpty {
                    AwaitingResolutionSection(
                        items: stale,
                        onReschedule: { item in rescheduleTarget = item },
                        onDone: { item in
                            Task {
                                await viewModel.markDone(taskId: item.task.id,
                                                         title: item.task.title,
                                                         estimatedMinutes: item.task.estimatedMinutes)
                            }
                        },
                        onRemove: { item in removeTarget = item }
                    )
                }

                if let task = ctx.bestTask {
                    BestNextActionCard(
                        task: task,
                        confidence: ctx.confidence,
                        loadExplanation: { await viewModel.fetchExplanation(taskId: task.id) },
                        onAgree: { Task { await viewModel.agree(taskId: task.id) } },
                        onDisagree: { disagreeTaskId = task.id },
                        onDone: {
                            Task { await viewModel.markDone(taskId: task.id, title: task.title,
                                                            estimatedMinutes: task.estimatedMinutes) }
                        },
                        onStart: {
                            viewModel.startTimer(taskId: task.id, title: task.title,
                                                 estimatedMinutes: task.estimatedMinutes)
                        },
                        onCancelTimer: { viewModel.cancelTimer(taskId: task.id) },
                        onSnooze: { Task { await viewModel.snooze(taskId: task.id) } }
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
                        icon: "checkmark.circle",
                        title: "You're all caught up",
                        message: "Nothing needs you right now. Capture a task and TimeSense will tell you what to do next."
                    )
                    .padding(.top, DesignTokens.Spacing.xl)
                }

                if let cards = ctx.context {
                    ContextGrid(cards: cards, onEnergyReported: { Task { await viewModel.load() } })
                        .padding(.top, DesignTokens.Spacing.xs)
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, 96)   // clear the custom tab bar (content can scroll under it in the pager)
        }
        .refreshable { await viewModel.load() }
    }
}

/// "TimeSense analyzed your day · Re-evaluated N min ago" — reassures the user the pick is fresh.
/// Ticks over time (every 15s) so the elapsed time actually counts up while the screen is open,
/// instead of appearing frozen at "just now".
private struct AnalysisBanner: View {
    let lastLoaded: Date?
    @State private var now = Date()
    private let ticker = Timer.publish(every: 15, on: .main, in: .common).autoconnect()

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
        .onReceive(ticker) { now = $0 }
        // Reset the clock when a fresh recommendation is loaded.
        .onChange(of: lastLoaded) { _, _ in now = Date() }
    }

    private var reevaluated: String {
        guard let lastLoaded else { return "Analyzing your day…" }
        let mins = Int(now.timeIntervalSince(lastLoaded) / 60)
        if mins <= 0 { return "Re-evaluated just now" }
        if mins == 1 { return "Re-evaluated 1 min ago" }
        return "Re-evaluated \(mins) min ago"
    }
}

/// Tasks whose deadline has already passed, and the three ways out.
///
/// TIME-309. `deadline_urgency` scores anything overdue at a flat 1.0 with no decay, so before this
/// existed a task due a week ago led the recommendation indefinitely — the app repeating the same
/// answer at a user who had evidently already decided not to act on it.
///
/// The backend demotes them so they stop leading. This section is the other half: demoting alone
/// just buries the problem. A passed deadline is a decision the user hasn't made yet, so the app
/// asks — once, calmly, in one place — instead of raising its voice.
private struct AwaitingResolutionSection: View {
    let items: [AwaitingResolution]
    let onReschedule: (AwaitingResolution) -> Void
    let onDone: (AwaitingResolution) -> Void
    let onRemove: (AwaitingResolution) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack(spacing: 6) {
                Image(systemName: "clock.badge.exclamationmark")
                    .font(.footnote)
                Text(items.count == 1 ? "Needs a decision" : "\(items.count) need a decision")
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
            }
            .foregroundColor(DesignTokens.Color.textSecondary)

            VStack(spacing: DesignTokens.Spacing.sm) {
                ForEach(items) { item in
                    AwaitingResolutionCard(
                        item: item,
                        onReschedule: { onReschedule(item) },
                        onDone: { onDone(item) },
                        onRemove: { onRemove(item) }
                    )
                }
            }
        }
    }
}

private struct AwaitingResolutionCard: View {
    let item: AwaitingResolution
    let onReschedule: () -> Void
    let onDone: () -> Void
    let onRemove: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
                Image(systemName: "calendar.badge.exclamationmark")
                    .font(.callout)
                    .foregroundColor(DesignTokens.Color.destructive)
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.task.title)
                        .font(DesignTokens.Typography.body.weight(.semibold))
                        .foregroundColor(DesignTokens.Color.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                    Text(item.ageLabel)
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.destructive)
                }
                Spacer(minLength: 0)
            }

            Text("This isn't being recommended any more. Give it a new date, or clear it.")
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: DesignTokens.Spacing.sm) {
                Button(action: onReschedule) {
                    Label("Reschedule", systemImage: "calendar")
                        .font(DesignTokens.Typography.footnote.weight(.semibold))
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)

                Button(action: onDone) {
                    Label("Done", systemImage: "checkmark")
                        .font(DesignTokens.Typography.footnote.weight(.semibold))
                }
                .buttonStyle(.bordered)
                .controlSize(.small)

                Spacer(minLength: 0)

                Button(role: .destructive, action: onRemove) {
                    Image(systemName: "trash")
                        .font(.footnote)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .accessibilityLabel("Remove task")
            }
        }
        .padding(DesignTokens.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous)
                .fill(DesignTokens.Color.destructive.opacity(0.10))
        )
    }
}

/// Picking a new deadline. Deliberately offers concrete near dates first — the point is to get the
/// task moving again, and a date picker as the only option is friction at exactly the moment the
/// user is least invested.
private struct RescheduleSheet: View {
    let item: AwaitingResolution
    let onPick: (Date) -> Void
    let onCancel: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var customDate = Date()

    /// 6pm, so a rescheduled task gets a plausible working deadline rather than midnight.
    private func atEvening(_ daysFromNow: Int) -> Date {
        let cal = Calendar.current
        let day = cal.date(byAdding: .day, value: daysFromNow, to: Date()) ?? Date()
        return cal.date(bySettingHour: 18, minute: 0, second: 0, of: day) ?? day
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Button("Today") { pick(atEvening(0)) }
                    Button("Tomorrow") { pick(atEvening(1)) }
                    Button("Next week") { pick(atEvening(7)) }
                } header: {
                    Text("New deadline")
                } footer: {
                    Text("Set to 6:00 PM so it has a realistic working deadline.")
                }

                Section("Pick a date") {
                    DatePicker("Due", selection: $customDate, displayedComponents: [.date, .hourAndMinute])
                    Button("Use this date") { pick(customDate) }
                }
            }
            .navigationTitle(item.task.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { onCancel(); dismiss() }
                }
            }
        }
    }

    private func pick(_ date: Date) {
        onPick(date)
        dismiss()
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
/// A prominent card for the engine's full cross-domain recommendation (from /now/recommendation).
private struct SuggestionCard: View {
    let suggestion: EngineRecommendation

    var body: some View {
        let accent = domainAccent(suggestion.domain)
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            HStack(spacing: 6) {
                Image(systemName: "sparkles").font(.footnote).foregroundStyle(accent)
                Text("TimeSense suggests")
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
                    .foregroundStyle(DesignTokens.Color.onHero.opacity(0.9))
                Spacer(minLength: 0)
                Text("\(Int((suggestion.confidence * 100).rounded()))% match")
                    .font(DesignTokens.Typography.caption.weight(.medium))
                    .foregroundStyle(DesignTokens.Color.onHero.opacity(0.9))
            }

            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(suggestion.title)
                        .font(DesignTokens.Typography.title.weight(.bold))
                        .foregroundStyle(DesignTokens.Color.onHero)
                        .fixedSize(horizontal: false, vertical: true)
                    Text(suggestion.message)
                        .font(DesignTokens.Typography.subheadline)
                        .foregroundStyle(DesignTokens.Color.onHero.opacity(0.82))
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: DesignTokens.Spacing.sm)
                HeroGlyph(systemName: icon, tint: accent)
            }

            if let travel = suggestion.travel {
                HeroPill(icon: "car.fill", text: travelLine(travel), tint: accent)
            }
        }
        .padding(DesignTokens.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(HeroBackground(accent: accent))
        .heroCardChrome(glow: accent)
    }

    private var icon: String {
        switch suggestion.domain {
        case "health": return "heart.fill"
        case "calendar": return "calendar"
        case "location": return "mappin.circle.fill"
        case "routine": return "repeat"
        case "planning": return "list.bullet.clipboard"
        case "context_switch": return "arrow.triangle.2.circlepath"
        default: return "sparkles"
        }
    }

    private func travelLine(_ t: EngineRecommendation.Travel) -> String {
        let place = suggestion.destinationPlace?.name ?? "There"
        var line = "\(place) · \(Int(t.durationMinutes.rounded())) min away"
        if t.fitsFreeBlock == true { line += " · fits your window" }
        return line
    }
}

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
    let onAgree: () -> Void
    let onDisagree: () -> Void
    let onDone: () -> Void
    let onStart: () -> Void
    let onCancelTimer: () -> Void
    let onSnooze: () -> Void

    var body: some View {
        let style = taskCategoryStyle(for: task.title)
        let accent = heroAccent(style.descriptor)
        VStack(spacing: 0) {
            heroHeader(style: style, accent: accent)
            footer
        }
        .heroCardChrome(glow: accent)
    }

    // Dark hero with a domain-coloured glow + glowing tinted glyph + dark signal pills.
    private func heroHeader(style: TaskCategoryStyle, accent: Color) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            HStack(spacing: 6) {
                Image(systemName: "sparkles").font(.footnote).foregroundStyle(accent)
                Text("Best Next Action")
                    .font(DesignTokens.Typography.footnote.weight(.semibold))
                    .foregroundStyle(DesignTokens.Color.onHero.opacity(0.9))
                Spacer(minLength: 0)
                Text("AI Recommended")
                    .font(DesignTokens.Typography.caption.weight(.semibold))
                    .foregroundStyle(DesignTokens.Color.onHero.opacity(0.9))
                    .padding(.horizontal, DesignTokens.Spacing.sm).padding(.vertical, 4)
                    .background(Capsule().fill(DesignTokens.Color.onHero.opacity(0.10)))
            }

            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(task.title)
                        .font(DesignTokens.Typography.title.weight(.bold))
                        .foregroundStyle(DesignTokens.Color.onHero)
                        .fixedSize(horizontal: false, vertical: true)
                    if let mins = task.estimatedMinutes {
                        Text("for \(mins) minutes")
                            .font(DesignTokens.Typography.title2.weight(.regular))
                            .foregroundStyle(DesignTokens.Color.onHero.opacity(0.82))
                    }
                }
                Spacer(minLength: DesignTokens.Spacing.sm)
                HeroGlyph(systemName: style.icon, tint: accent)
            }

            HStack(spacing: DesignTokens.Spacing.sm) {
                HeroPill(icon: style.icon, text: style.descriptor, tint: accent)
                if task.priority <= 2 { HeroPill(icon: "flag.fill", text: "High priority", tint: Cosmic.red) }
                if let mins = task.estimatedMinutes { HeroPill(icon: "clock", text: "\(mins) min", tint: DesignTokens.Color.onHero.opacity(0.8)) }
            }
        }
        .padding(DesignTokens.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(HeroBackground(accent: accent))
    }

    // Surface bottom: confidence + Why + quick actions stay readable on a solid card.
    private var footer: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
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
            QuickActionRow(onAgree: onAgree, onDisagree: onDisagree, onDone: onDone,
                           taskId: task.id, onStart: onStart,
                           onCancelTimer: onCancelTimer, onSnooze: onSnooze)
                .id(task.id)  // reset the Agree/Disagree stage whenever the recommendation changes
        }
        .padding(DesignTokens.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Cosmic.surface)
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
    // Deadlines / money / anything time-critical → red (checked first so it wins).
    if has(["pay", "invoice", "bill", "rent", "tax", "taxes", "deadline", "due", "submit", "file ", "renew"]) {
        return TaskCategoryStyle(icon: "exclamationmark.circle.fill", color: Cosmic.red, descriptor: "Deadline")
    }
    if has(["revise", "paper", "write", "draft", "essay", "report", "document", "proposal", "read", "study", "research", "deck", "slides"]) {
        return TaskCategoryStyle(icon: "doc.text.fill", color: Cosmic.blue, descriptor: "Focus task")
    }
    if has(["jira", "ticket", "review", "code", "bug", "pr ", "pull request"]) {
        return TaskCategoryStyle(icon: "checklist", color: Cosmic.blue, descriptor: "Focus task")
    }
    if has(["email", "reply", "respond", "inbox", "message", "slack"]) {
        return TaskCategoryStyle(icon: "envelope.fill", color: Cosmic.amber, descriptor: "Email")
    }
    if has(["walk", "run", "gym", "exercise", "workout", "stretch", "yoga", "break", "meditate", "water"]) {
        return TaskCategoryStyle(icon: "figure.walk", color: Cosmic.green, descriptor: "Health break")
    }
    if has(["call", "phone", "dial", "text ", "ping"]) {
        return TaskCategoryStyle(icon: "phone.fill", color: Cosmic.yellow, descriptor: "Quick task")
    }
    if has(["buy", "shop", "store", "groceries", "grocery", "home depot", "mall", "walmart", "target", "market", "errand", "gift", "pick up", "pickup", "pharmacy", "prescription"]) {
        return TaskCategoryStyle(icon: "cart.fill", color: Cosmic.orange, descriptor: "Errand", locationAware: true)
    }
    if has(["clean", "laundry", "dishes", "tidy", "vacuum", "organize", "trash", "chore"]) {
        return TaskCategoryStyle(icon: "checklist", color: Cosmic.yellow, descriptor: "Chore")
    }
    if has(["meeting", "standup", "sync", "1:1", "interview", "call with"]) {
        return TaskCategoryStyle(icon: "person.2.fill", color: Cosmic.violet, descriptor: "Meeting")
    }
    if has(["doctor", "dentist", "appointment", "chiropractor", "clinic", "checkup"]) {
        return TaskCategoryStyle(icon: "cross.case.fill", color: Cosmic.violet, descriptor: "Appointment", locationAware: true)
    }
    if has(["family", "kids", "wife", "husband", "date night", "birthday", "home"]) {
        return TaskCategoryStyle(icon: "house.fill", color: Cosmic.yellow, descriptor: "Personal")
    }
    return TaskCategoryStyle(icon: "checkmark.circle.fill", color: Cosmic.blue, descriptor: "Task")
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
    /// False when opened for one of the "other good options" — so it isn't mislabeled as the top pick.
    var isTopPick: Bool = true
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    RecommendedActionHeaderCard(
                        action: explanation.recommendedAction,
                        confidence: explanation.confidence,
                        isTopPick: isTopPick
                    )

                    if !explanation.summary.isEmpty {
                        header("Summary")
                        Text(explanation.summary)
                            .font(DesignTokens.Typography.subheadline)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(DesignTokens.Spacing.lg)
                            .cardStyle()
                    }

                    header("Signals analyzed")
                    SignalsCard(signals: explanation.signals ?? [])

                    if !explanation.alternativesConsidered.isEmpty {
                        header("Alternatives considered")
                        AlternativesCard(alternatives: explanation.alternativesConsidered)
                    }

                    Text("Evaluated just now")
                        .font(DesignTokens.Typography.caption)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                }
                .padding(.horizontal, DesignTokens.Spacing.lg)
                .padding(.vertical, DesignTokens.Spacing.md)
            }
            .background(CosmicBackground())
            .navigationTitle(isTopPick ? "Why this recommendation?" : "About this option")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
            }
        }
    }

    private func header(_ text: String) -> some View {
        Text(text)
            .font(DesignTokens.Typography.headline)
            .foregroundColor(DesignTokens.Color.accent)
            .padding(.horizontal, DesignTokens.Spacing.xs)
            .padding(.top, DesignTokens.Spacing.xs)
    }
}

private struct RecommendedActionHeaderCard: View {
    let action: RecommendationExplanation.Action
    let confidence: Double
    var isTopPick: Bool = true

    var body: some View {
        let style = taskCategoryStyle(for: action.title)
        let accent = heroAccent(style.descriptor)
        HStack(alignment: .center, spacing: DesignTokens.Spacing.md) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                HStack(spacing: 6) {
                    Image(systemName: isTopPick ? "sparkles" : "list.bullet").font(.caption).foregroundStyle(accent)
                    Text(isTopPick ? "Recommended action" : "Also a good option")
                        .font(DesignTokens.Typography.footnote.weight(.semibold))
                        .foregroundStyle(DesignTokens.Color.onHero.opacity(0.9))
                }
                HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
                    Image(systemName: style.icon)
                        .font(.title2).foregroundStyle(accent)
                        .shadow(color: accent.opacity(0.6), radius: 8)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(action.title)
                            .font(DesignTokens.Typography.headline)
                            .foregroundStyle(DesignTokens.Color.onHero)
                            .fixedSize(horizontal: false, vertical: true)
                        if let m = action.recommendedDurationMinutes {
                            Text("for \(m) minutes")
                                .font(DesignTokens.Typography.footnote)
                                .foregroundStyle(DesignTokens.Color.onHero.opacity(0.8))
                        }
                    }
                }
            }
            Spacer(minLength: 0)
            ConfidenceRing(value: confidence, tint: accent, onDark: true)
        }
        .padding(DesignTokens.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(HeroBackground(accent: accent))
        .heroCardChrome(glow: accent)
    }
}

struct ConfidenceRing: View {
    let value: Double
    var tint: Color = DesignTokens.Color.accent
    var onDark: Bool = false

    var body: some View {
        ZStack {
            Circle().stroke(tint.opacity(0.2), lineWidth: 7)
            Circle()
                .trim(from: 0, to: value)
                .stroke(tint, style: StrokeStyle(lineWidth: 7, lineCap: .round))
                .rotationEffect(.degrees(-90))
            Text("\(Int((value * 100).rounded()))%")
                .font(DesignTokens.Typography.headline)
                .foregroundStyle(onDark ? DesignTokens.Color.onHero : DesignTokens.Color.textPrimary)
                .monospacedDigit()
        }
        .frame(width: 68, height: 68)
    }
}

private struct SignalsCard: View {
    let signals: [RecommendationExplanation.Signal]

    var body: some View {
        VStack(spacing: 0) {
            ForEach(Array(signals.enumerated()), id: \.element.id) { idx, signal in
                let s = signalStyle(signal.name)
                HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
                    RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous)
                        .fill(s.color.opacity(0.16))
                        .frame(width: 38, height: 38)
                        .overlay(Image(systemName: s.icon).foregroundColor(s.color))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(signal.name)
                            .font(DesignTokens.Typography.callout.weight(.semibold))
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        Text(signal.detail)
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    Spacer(minLength: DesignTokens.Spacing.sm)
                    Image(systemName: signal.available ? "checkmark.circle.fill" : "circle")
                        .foregroundColor(signal.available ? Cosmic.green : DesignTokens.Color.textSecondary.opacity(0.4))
                }
                .padding(DesignTokens.Spacing.md)
                if idx < signals.count - 1 { Divider().padding(.leading, 62) }
            }
        }
        .cardStyle()
    }

    private func signalStyle(_ name: String) -> (icon: String, color: Color) {
        switch name {
        case "Calendar":    return ("calendar", Cosmic.blue)
        case "Time of day": return ("sun.max.fill", Cosmic.amber)
        case "Location":    return ("mappin.circle.fill", Cosmic.cyan)
        case "Priority":    return ("flag.fill", Cosmic.violet)
        case "Energy":      return ("bolt.fill", Cosmic.green)
        default:            return ("circle.fill", Cosmic.blue)
        }
    }
}

private struct AlternativesCard: View {
    let alternatives: [RecommendationExplanation.Alternative]

    var body: some View {
        VStack(spacing: 0) {
            ForEach(Array(alternatives.enumerated()), id: \.element.id) { idx, alt in
                let style = taskCategoryStyle(for: alt.title)
                HStack(spacing: DesignTokens.Spacing.md) {
                    RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous)
                        .fill(style.color.opacity(0.16))
                        .frame(width: 38, height: 38)
                        .overlay(Image(systemName: style.icon).foregroundColor(style.color))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(alt.title)
                            .font(DesignTokens.Typography.callout.weight(.semibold))
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        Text(alt.reasonNotSelected)
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    Spacer(minLength: 0)
                    // These rows are informational (why each wasn't picked) — no chevron, since they
                    // aren't tappable. The tappable runner-ups live in "Other good options".
                }
                .padding(DesignTokens.Spacing.md)
                if idx < alternatives.count - 1 { Divider().padding(.leading, 62) }
            }
        }
        .cardStyle()
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
            if let explanation { RecommendationExplanationSheet(explanation: explanation, isTopPick: false) }
        }
    }

    private func subtitle(style: TaskCategoryStyle) -> String {
        if let m = task.estimatedMinutes { return "\(m) min  ·  \(style.descriptor)" }
        return style.descriptor
    }
}

/// Two-stage feedback: first ask whether the user agrees with the recommendation. On Agree, reveal
/// Done/Snooze to act on it. On Disagree, the view model records it and surfaces a different action
/// (the parent resets this view via `.id(task.id)` when the recommendation changes).
private struct QuickActionRow: View {
    let onAgree: () -> Void
    let onDisagree: () -> Void
    let onDone: () -> Void
    let taskId: String
    let onStart: () -> Void
    let onCancelTimer: () -> Void
    let onSnooze: () -> Void

    @State private var agreed = false
    /// Observed, not copied: a persisted timer is the source of truth, so the row can be recreated
    /// (tab switch, recommendation change, cold launch) and still show the timer running (TIME-298).
    /// Elapsed time is read from it live — never passed in as a value (TIME-306).
    @ObservedObject private var timers = TaskTimerStore.shared

    /// True when this task is the one being timed — read from the store, never from local @State.
    private var timing: Bool { timers.isTiming(taskId: taskId) }

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.sm) {
            HStack(spacing: DesignTokens.Spacing.sm) {
                if agreed {
                    PrimaryAction(title: "Done", systemImage: "checkmark.circle.fill", action: onDone)
                    SecondaryAction(title: "Snooze", systemImage: "clock.arrow.2.circlepath",
                                    action: onSnooze)
                } else {
                    PrimaryAction(title: "Agree", systemImage: "hand.thumbsup.fill") {
                        withAnimation(.easeInOut(duration: 0.18)) { agreed = true }
                        onAgree()
                    }
                    SecondaryAction(title: "Disagree", systemImage: "hand.thumbsdown",
                                    action: onDisagree)
                }
            }

            // Optional timer. The point is a real duration captured with NO prompt at all — the
            // best learning signal, because it costs the user nothing to give (TIME-287).
            // Shown whenever a timer is running for this task, even if the user hasn't tapped Agree
            // in this instance of the view — otherwise returning to the tab hides a live timer.
            if agreed || timing {
                Button {
                    if timing { onCancelTimer() } else { onStart() }
                } label: {
                    if timing {
                        // TimelineView drives the redraw, so the framework guarantees a tick every
                        // second. The previous version used @State + Timer.publish and read elapsed
                        // time from a `let` handed down by the parent — a SNAPSHOT taken when Start
                        // was tapped, which never recomputed, so it rendered 0:00 forever (TIME-306).
                        TimelineView(.periodic(from: .now, by: 1)) { context in
                            HStack(spacing: 6) {
                                // Blink derived from the timeline's own clock rather than an
                                // implicit animation on @State, which a re-render can cancel and
                                // leave sitting static.
                                Circle()
                                    .fill(Cosmic.green)
                                    .frame(width: 7, height: 7)
                                    .opacity(Int(context.date.timeIntervalSince1970) % 2 == 0 ? 1.0 : 0.3)
                                    .animation(.easeInOut(duration: 0.45), value: context.date)
                                Text(liveLabel(at: context.date))
                                    .monospacedDigit()   // stops the label jittering as digits change
                            }
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        }
                    } else {
                        Label("Start timer", systemImage: "play.circle")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                    }
                }
                .buttonStyle(.plain)
                .accessibilityLabel(timing ? "Stop timing this task" : "Start timing this task")
                .accessibilityValue(timing ? liveLabel(at: Date()) : "")
            }
        }
        // A running timer means the user already committed to this task, so don't send them back
        // through Agree — that was the reported "I have to choose to do the task again" (TIME-298).
        .onAppear { if timing { agreed = true } }
        .onChange(of: timing) { _, isTiming in
            if isTiming { agreed = true }
        }
    }

    /// Elapsed time computed from the STORE at the given instant.
    ///
    /// Reading the store here, rather than accepting a value from the parent, is the fix for
    /// TIME-306: a value passed in is fixed at the parent's last render and cannot advance no
    /// matter how often this view redraws.
    private func liveLabel(at now: Date) -> String {
        guard let running = timers.running, running.taskId == taskId else { return "Start timer" }
        return running.label(at: now)
    }
}

private struct PrimaryAction: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .font(DesignTokens.Typography.subheadline.weight(.semibold))
                .lineLimit(1)
                .foregroundColor(DesignTokens.Color.onHero)
                .frame(maxWidth: .infinity)
                .padding(.vertical, DesignTokens.Spacing.sm)
                .background(DesignTokens.Color.accent)
                .clipShape(Capsule())
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


// MARK: - Glanceable dashboard (calendar / tasks / energy / nearby) — real signals only

private struct ContextGrid: View {
    let cards: NowContextCards
    /// Called after a check-in so Now re-fetches — the correction should visibly change the
    /// recommendation, not just the card.
    var onEnergyReported: () -> Void = {}

    @EnvironmentObject private var appState: AppState
    @State private var showEnergyCheckIn = false
    private let cols = [GridItem(.flexible(), spacing: DesignTokens.Spacing.md),
                        GridItem(.flexible(), spacing: DesignTokens.Spacing.md)]

    var body: some View {
        grid
            .confirmationDialog("How's your energy right now?",
                                isPresented: $showEnergyCheckIn, titleVisibility: .visible) {
                Button("Running low") { report("low") }
                Button("Okay") { report("medium") }
                Button("Good") { report("high") }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This overrides what we estimated, for the next few hours.")
            }
    }

    private func report(_ level: String) {
        Task {
            struct Body: Encodable { let reported: String }
            struct Resp: Decodable { let level: String }
            let _: Resp? = try? await APIClient.shared.post(
                "/api/v1/energy/checkin", body: Body(reported: level)
            )
            onEnergyReported()
        }
    }

    private var grid: some View {
        LazyVGrid(columns: cols, spacing: DesignTokens.Spacing.md) {
            if let title = cards.nextEventTitle {
                ContextCard(label: "Calendar", icon: "calendar", tint: Cosmic.blue,
                            value: eventTime, sub: eventSub(title))
            }
            // Tapping the Tasks card jumps to the Today task list.
            Button { appState.selectedTab = .today } label: {
                ContextCard(label: "Tasks", icon: "checkmark.circle.fill", tint: Cosmic.violet,
                            value: "\(cards.tasksDueToday)", sub: taskSub)
            }
            .buttonStyle(.plain)
            if let steps = cards.steps {
                ContextCard(label: "Steps", icon: "figure.walk", tint: Cosmic.blue,
                            value: steps.formatted(), sub: stepsSub(steps))
            }
            // Tapping Energy lets the user correct it in one tap. Inferred energy reads sleep,
            // activity and the clock — proxies, not the person — so a correction has to be cheap
            // and has to actually drive recommendations (TIME-289).
            if let energy = cards.energyLevel {
                Button { showEnergyCheckIn = true } label: {
                    ContextCard(label: "Energy", icon: "bolt.fill", tint: Cosmic.green,
                                value: energy.capitalized, sub: energySub)
                }
                .buttonStyle(.plain)
            }
            if let place = cards.currentPlace {
                ContextCard(label: "Nearby", icon: "location.fill", tint: Cosmic.cyan,
                            value: place, sub: "You're here now")
            }
        }
    }

    private var eventTime: String {
        cards.nextEventAt?.formatted(date: .omitted, time: .shortened) ?? "—"
    }
    private func eventSub(_ title: String) -> String {
        guard let mins = cards.nextEventInMinutes, mins > 0 else { return title }
        let h = mins / 60, m = mins % 60
        let when = h > 0 ? "in \(h)h \(m)m" : "in \(m)m"
        return "\(title) · \(when)"
    }
    private var taskSub: String {
        let noun = cards.tasksDueToday == 1 ? "task due today" : "tasks due today"
        return "\(noun) · \(cards.tasksCompletedToday) done"
    }
    private var energySub: String {
        if let m = cards.inactiveMinutes, m >= 60 { return "Sitting \(m)m — time to move" }
        if let h = cards.sleepHours { return "\(h.formatted(.number.precision(.fractionLength(0...1))))h last night" }
        return "based on your sleep"
    }
    private func stepsSub(_ steps: Int) -> String {
        let goal = cards.stepsGoal ?? 10000
        if let ex = cards.exerciseMinutes, ex > 0 { return "\(ex) active min · goal \(goal.formatted())" }
        return "of \(goal.formatted()) goal"
    }
}

private struct ContextCard: View {
    let label: String
    let icon: String
    let tint: Color
    let value: String
    let sub: String?

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack(spacing: 6) {
                Image(systemName: icon).font(.caption).foregroundColor(tint)
                Text(label.uppercased())
                    .font(DesignTokens.Typography.caption.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .tracking(DesignTokens.Tracking.wide)
            }
            Text(value)
                .font(DesignTokens.Typography.title2.weight(.bold))
                .foregroundColor(tint)
                .lineLimit(1).minimumScaleFactor(0.6)
            if let sub {
                Text(sub)
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .lineLimit(2).fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, minHeight: 112, alignment: .leading)
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}

// MARK: - Duration feedback

/// "How long did that take?" — the sheet that replaced three fixed buttons.
///
/// Those buttons could only ever offer 15 / 30 / 60 minutes, and feeding those coarse answers into
/// the estimator is what produced the "everything takes 23 minutes" report: a 15 followed by two
/// 30s blended to exactly 23, which then answered for nearly every task (TIME-286).
///

// MARK: - Swap: "what would you rather do?"

struct SwapPrompt: Identifiable, Equatable {
    let rejectedTaskId: String
    let reason: String?
    var id: String { rejectedTaskId + (reason ?? "") }
}

/// After the user says why a recommendation is wrong, offer today's other tasks so they can say
/// what they'd rather do.
///
/// Why this is worth a whole screen: a rejection tells the assistant a pick was wrong; a swap tells
/// it what would have been RIGHT, in a known context. That pairing is the strongest feedback the
/// product can collect (TIME-294/296).
///
/// It stays optional. "Not now" dismisses without choosing, and the disagree is still recorded —
/// the user must never be made to answer a second question to register a simple no.
struct SwapPickerSheet: View {
    let prompt: SwapPrompt
    let loadCandidates: () async -> [TimelineTask]
    let onPick: (String) -> Void
    let onSkip: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var candidates: [TimelineTask] = []
    @State private var loading = true

    var body: some View {
        NavigationStack {
            Group {
                if loading {
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if candidates.isEmpty {
                    // Nothing else to offer — say so plainly instead of showing an empty list.
                    VStack(spacing: DesignTokens.Spacing.md) {
                        Image(systemName: "checkmark.circle")
                            .font(.system(size: 44))
                            .foregroundColor(DesignTokens.Color.textSecondary)
                        Text("Nothing else on today")
                            .font(DesignTokens.Typography.headline)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        Text("We've recorded that this one wasn't right.")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding(DesignTokens.Spacing.xl)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List {
                        ForEach(candidates) { task in
                        Button {
                            onPick(task.id)
                            dismiss()
                        } label: {
                            HStack(spacing: DesignTokens.Spacing.md) {
                                let style = taskCategoryStyle(for: task.title)
                                Image(systemName: style.icon)
                                    .foregroundColor(style.color)
                                    .frame(width: 24)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(task.title)
                                        .font(DesignTokens.Typography.callout)
                                        .foregroundColor(DesignTokens.Color.textPrimary)
                                        .lineLimit(2)
                                    if let minutes = task.estimatedMinutes {
                                        Text("~\(minutes) min")
                                            .font(DesignTokens.Typography.footnote)
                                            .foregroundColor(DesignTokens.Color.textSecondary)
                                    }
                                }
                                Spacer(minLength: 0)
                            }
                        }
                        .buttonStyle(.plain)
                        }
                    }
                }
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("What would you rather do?")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Not now") { onSkip(); dismiss() }
                }
            }
            .task {
                candidates = await loadCandidates()
                loading = false
            }
        }
    }
}

// MARK: - Timer overrun

/// "Still on this?" — shown when a running timer has passed its estimate by a clear margin.
///
/// A timer with no end condition is the real problem it solves: a task finished without stopping
/// the timer keeps counting, and eventually either submits nothing (the plausibility guard discards
/// it) or a wildly inflated duration that poisons the learned estimate for that task type.
///
/// It asks rather than acting. Auto-completing the task would be the same trust violation as
/// writing to someone's calendar without approval — the assistant suggests, the user decides. And
/// it appears once per timer: "Still going" is remembered, because the product rule against nagging
/// applies to this as much as to notifications.
struct TimerOverrunCard: View {
    let timer: RunningTaskTimer
    let onDone: () -> Void
    let onStillGoing: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "stopwatch")
                    .foregroundColor(Cosmic.orange)
                Text("Still on “\(timer.taskTitle)”?")
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(2)
            }

            Text("You've been timing this for \(formatElapsed(timer.elapsed)) — we expected about \(timer.expectedMinutes) min.")
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)

            HStack(spacing: DesignTokens.Spacing.sm) {
                Button(action: onDone) {
                    Label("It's done", systemImage: "checkmark.circle.fill")
                        .font(DesignTokens.Typography.subheadline.weight(.semibold))
                        .foregroundColor(DesignTokens.Color.onHero)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, DesignTokens.Spacing.sm)
                        .background(DesignTokens.Color.accent)
                        .clipShape(Capsule())
                }
                Button(action: onStillGoing) {
                    Text("Still going")
                        .font(DesignTokens.Typography.subheadline)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, DesignTokens.Spacing.sm)
                        .overlay(Capsule().stroke(DesignTokens.Color.hairline, lineWidth: 1))
                }
            }
        }
        .padding(DesignTokens.Spacing.lg)
        .cardStyle()
    }
}
