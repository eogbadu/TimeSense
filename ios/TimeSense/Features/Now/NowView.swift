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
            .background(CosmicBackground())
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

                // A full cross-domain engine suggestion (wind-down, prep-for-meeting, nearby errand…)
                // supersedes the simpler local wind-down nudge when available.
                if let suggestion = viewModel.suggestion, suggestion.isCrossDomainAction {
                    SuggestionCard(suggestion: suggestion)
                } else if let moment = ctx.moment, !moment.isEmpty {
                    MomentCard(text: moment)
                }

                if let task = ctx.bestTask {
                    BestNextActionCard(
                        task: task,
                        confidence: ctx.confidence,
                        loadExplanation: { await viewModel.fetchExplanation(taskId: task.id) },
                        onAgree: { Task { await viewModel.agree(taskId: task.id) } },
                        onDisagree: { Task { await viewModel.disagree(taskId: task.id) } },
                        onDone: { Task { await viewModel.markDone(taskId: task.id, title: task.title) } },
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
                        icon: "sparkles",
                        title: "You're all caught up",
                        message: "Nothing needs you right now. Capture a task and TimeSense will tell you what to do next."
                    )
                    .padding(.top, DesignTokens.Spacing.xl)
                }

                if let cards = ctx.context {
                    ContextGrid(cards: cards).padding(.top, DesignTokens.Spacing.xs)
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
            QuickActionRow(onAgree: onAgree, onDisagree: onDisagree, onDone: onDone, onSnooze: onSnooze)
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
        return TaskCategoryStyle(icon: "sparkles", color: Cosmic.yellow, descriptor: "Chore")
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
    let onSnooze: () -> Void

    @State private var agreed = false

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            if agreed {
                PrimaryAction(title: "Done", systemImage: "checkmark.circle.fill", action: onDone)
                SecondaryAction(title: "Snooze", systemImage: "clock.arrow.2.circlepath", action: onSnooze)
            } else {
                PrimaryAction(title: "Agree", systemImage: "hand.thumbsup.fill") {
                    withAnimation(.easeInOut(duration: 0.18)) { agreed = true }
                    onAgree()
                }
                SecondaryAction(title: "Disagree", systemImage: "hand.thumbsdown", action: onDisagree)
            }
        }
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
    @EnvironmentObject private var appState: AppState
    private let cols = [GridItem(.flexible(), spacing: DesignTokens.Spacing.md),
                        GridItem(.flexible(), spacing: DesignTokens.Spacing.md)]

    var body: some View {
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
            if let energy = cards.energyLevel {
                ContextCard(label: "Energy", icon: "bolt.fill", tint: Cosmic.green,
                            value: energy.capitalized, sub: energySub)
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
