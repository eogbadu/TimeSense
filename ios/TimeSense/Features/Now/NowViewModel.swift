import Foundation
import WidgetKit

struct NowContext: Decodable {
    let greeting: String
    let usableMinutes: Int
    let bestTask: NowTask?
    let reason: String?
    let alternatives: [NowTask]?
    let confidence: Double?
    let moment: String?
    let feasibility: Feasibility?
    let context: NowContextCards?
    let recommendationEventId: String?
    /// Tasks whose deadline passed on an earlier day — demoted out of the top slot but still
    /// visible, waiting for the user to reschedule, complete, or remove them (TIME-309).
    let awaitingResolution: [AwaitingResolution]?

    enum CodingKeys: String, CodingKey {
        case greeting
        case usableMinutes = "usable_minutes"
        case bestTask = "best_task"
        case reason
        case alternatives
        case confidence
        case moment
        case feasibility
        case context
        case recommendationEventId = "recommendation_event_id"
        case awaitingResolution = "awaiting_resolution"
    }
}

/// A task the assistant has stopped recommending because its deadline has passed, paired with how
/// long ago that was. The app asks instead of repeating itself: a deadline a week gone is not a
/// statement about what to do now, it is a decision the user hasn't made yet (TIME-309).
struct AwaitingResolution: Decodable, Identifiable {
    let task: NowTask
    let daysOverdue: Int

    var id: String { task.id }

    enum CodingKeys: String, CodingKey {
        case task
        case daysOverdue = "days_overdue"
    }

    /// "Due yesterday" reads better than "1 day past due", and the plural matters at a glance.
    var ageLabel: String {
        switch daysOverdue {
        case ...0: return "Past due"
        case 1: return "Due yesterday"
        case 2...6: return "\(daysOverdue) days past due"
        case 7...13: return "Over a week past due"
        default: return "Over \(daysOverdue / 7) weeks past due"
        }
    }
}

/// Glanceable dashboard signals for the Now screen (calendar / tasks / energy / nearby).
struct NowContextCards: Decodable {
    let nextEventTitle: String?
    let nextEventAt: Date?
    let nextEventInMinutes: Int?
    let tasksDueToday: Int
    let tasksCompletedToday: Int
    let energyLevel: String?
    let sleepHours: Double?
    let currentPlace: String?
    let steps: Int?
    let stepsGoal: Int?
    let activeEnergyKcal: Int?
    let exerciseMinutes: Int?
    let inactiveMinutes: Int?

    enum CodingKeys: String, CodingKey {
        case nextEventTitle = "next_event_title"
        case nextEventAt = "next_event_at"
        case nextEventInMinutes = "next_event_in_minutes"
        case tasksDueToday = "tasks_due_today"
        case tasksCompletedToday = "tasks_completed_today"
        case energyLevel = "energy_level"
        case sleepHours = "sleep_hours"
        case currentPlace = "current_place"
        case steps
        case stepsGoal = "steps_goal"
        case activeEnergyKcal = "active_energy_kcal"
        case exerciseMinutes = "exercise_minutes"
        case inactiveMinutes = "inactive_minutes"
    }
}

struct Feasibility: Decodable {
    let fits: Bool
    let message: String   // already includes the suggested slot time, formatted
}

struct NowTask: Decodable, Identifiable {
    let id: String
    let title: String
    let status: String
    let estimatedMinutes: Int?
    let priority: Int
    let dueAt: Date?

    enum CodingKeys: String, CodingKey {
        case id, title, status, priority
        case estimatedMinutes = "estimated_minutes"
        case dueAt = "due_at"
    }
}

struct DurationPrompt: Identifiable, Equatable {
    let id: String   // the completed task's id
    let title: String
    /// What the assistant predicted — the sheet opens on this so the common case ("about right")
    /// is a single tap, and only a real disagreement costs any effort.
    let estimatedMinutes: Int?
    /// The library type this will teach. Shown so a wrong guess can be corrected, since a wrong
    /// type teaches the wrong bucket (TIME-286).
    let taskType: String?
    /// Minutes measured by the in-app timer, when the user used it. Pre-fills the sheet with a real
    /// figure rather than a guess.
    let measuredMinutes: Int?
}

struct RecommendationExplanation: Decodable {
    struct Action: Decodable { let title: String; let recommendedDurationMinutes: Int?
        enum CodingKeys: String, CodingKey { case title; case recommendedDurationMinutes = "recommended_duration_minutes" } }
    struct Factor: Decodable, Identifiable { let name: String; let rating: String; var id: String { name } }
    struct Alternative: Decodable, Identifiable {
        let taskId: String; let title: String; let reasonNotSelected: String
        var id: String { taskId }
        enum CodingKeys: String, CodingKey { case taskId = "task_id"; case title; case reasonNotSelected = "reason_not_selected" }
    }
    struct Signal: Decodable, Identifiable {
        let name: String; let detail: String; let available: Bool
        var id: String { name }
    }
    let recommendedAction: Action
    let confidence: Double
    let contextUsed: [String]
    let decisionFactors: [Factor]
    let signals: [Signal]?
    let alternativesConsidered: [Alternative]
    let summary: String

    enum CodingKeys: String, CodingKey {
        case recommendedAction = "recommended_action"
        case confidence
        case contextUsed = "context_used"
        case decisionFactors = "decision_factors"
        case signals
        case alternativesConsidered = "alternatives_considered"
        case summary
    }
}

enum NowUiState {
    case idle
    case loading
    case loaded(NowContext)
    case error(String)
}

/// The full cross-domain engine recommendation from /now/recommendation (any domain, LLM-phrased).
struct EngineRecommendation: Decodable {
    let actionType: String
    let domain: String
    let title: String
    let message: String
    let explanation: String
    let confidence: Double
    let reasonCodes: [String]
    let eligibleForPush: Bool
    let relatedTaskId: String?
    let travel: Travel?
    let destinationPlace: Place?

    struct Travel: Decodable {
        let distanceMiles: Double
        let durationMinutes: Double
        let fitsFreeBlock: Bool?
        enum CodingKeys: String, CodingKey {
            case distanceMiles = "distance_miles"
            case durationMinutes = "duration_minutes"
            case fitsFreeBlock = "fits_free_block"
        }
    }
    struct Place: Decodable { let name: String }

    enum CodingKeys: String, CodingKey {
        case actionType = "action_type", domain, title, message, explanation, confidence
        case reasonCodes = "reason_codes", eligibleForPush = "eligible_for_push"
        case relatedTaskId = "related_task_id", travel, destinationPlace = "destination_place"
    }

    /// A pure cross-domain nudge (wind-down, prep-for-meeting, errand…) — i.e. not the task the
    /// best-action card already shows. Worth surfacing separately.
    var isCrossDomainAction: Bool { relatedTaskId == nil }
}

@MainActor
final class NowViewModel: ObservableObject {
    @Published var uiState: NowUiState = .idle
    /// When the recommendation was last (re-)computed — drives the "Re-evaluated X min ago" banner.
    @Published var lastLoaded: Date?
    /// The full engine recommendation (fetched lazily after the fast /now payload).
    @Published var suggestion: EngineRecommendation?

    var context: NowContext? {
        if case .loaded(let c) = uiState { return c }
        return nil
    }

    func load() async {
        uiState = .loading
        do {
            let ctx: NowContext = try await APIClient.shared.get("/api/v1/now")
            uiState = .loaded(ctx)
            lastLoaded = Date()
            updateWidgetSnapshot(with: ctx)
        } catch {
            uiState = .error(error.localizedDescription)
            return
        }
        // Lazily fetch the full cross-domain engine recommendation (LLM-backed, slower) so the fast
        // /now payload renders first.
        suggestion = try? await APIClient.shared.get("/api/v1/now/recommendation")
    }

    /// Updates only the fields this endpoint knows about, preserving whatever TodayViewModel
    /// last wrote for nextEvent, then asks WidgetKit to refresh.
    private func updateWidgetSnapshot(with ctx: NowContext) {
        var snapshot = WidgetSnapshot.load() ?? .empty
        snapshot.usableMinutes = ctx.usableMinutes
        snapshot.bestTask = ctx.bestTask.map {
            WidgetSnapshot.Task(id: $0.id, title: $0.title, estimatedMinutes: $0.estimatedMinutes)
        }
        snapshot.updatedAt = Date()
        snapshot.save()
        WidgetCenter.shared.reloadAllTimelines()
    }

    /// Set when a just-completed task should trigger the "How long did that take?" prompt (only
    /// while the assistant is still learning that kind of task).
    @Published var durationPrompt: DurationPrompt?

    /// The running timer lives in TaskTimerStore, which persists it. It used to be an in-memory
    /// dictionary here, mirrored in @State on the button row — so it was lost both when SwiftUI
    /// recreated the row (tab switch, recommendation change) and when the app was force-quit
    /// (TIME-298).
    private var timers: TaskTimerStore { TaskTimerStore.shared }

    func startTimer(taskId: String, title: String, estimatedMinutes: Int?) {
        timers.start(taskId: taskId, title: title, estimatedMinutes: estimatedMinutes)
    }

    func cancelTimer(taskId: String) {
        timers.stopIfTiming(taskId: taskId)
    }

    func isTiming(taskId: String) -> Bool { timers.isTiming(taskId: taskId) }

    /// Raw elapsed seconds, for the live display. Deliberately NOT clamped: the user should see the
    /// first seconds tick by, which is the only evidence the timer is actually running.
    func elapsedSeconds(taskId: String) -> TimeInterval? {
        timers.elapsed(taskId: taskId)
    }

    /// Whole minutes, for SUBMISSION. The plausibility guard applies here and only here — a timer
    /// left running overnight must not poison the learned estimate, but it also shouldn't stop the
    /// display from working in the first minute.
    func elapsedMinutes(taskId: String) -> Int? {
        guard let seconds = timers.elapsed(taskId: taskId) else { return nil }
        return Self.plausibleMinutes(seconds / 60)
    }

    /// Guard against a timer left running overnight, or one stopped a few seconds after starting —
    /// neither is a real observation, and feeding them in would poison the learned estimate.
    static func plausibleMinutes(_ raw: Double) -> Int? {
        let rounded = Int(raw.rounded())
        return (1...480).contains(rounded) ? rounded : nil
    }

    func markDone(taskId: String, title: String, estimatedMinutes: Int? = nil) async {
        guard case .loaded = uiState else { return }
        let measured = elapsedMinutes(taskId: taskId)
        struct StatusUpdate: Encodable { let status: String }
        do {
            let _: TaskPatchResponse = try await APIClient.shared.patch(
                "/api/v1/tasks/\(taskId)", body: StatusUpdate(status: "done")
            )
            await maybePromptDuration(taskId: taskId, title: title,
                                      estimatedMinutes: estimatedMinutes, measured: measured)
            timers.stopIfTiming(taskId: taskId)
            await load()
        } catch {
            // Reload anyway so UI stays consistent
            await load()
        }
    }

    // MARK: - Resolving a passed deadline (TIME-309)
    //
    // A stale task is demoted by the backend so it stops leading the recommendation, but demoting is
    // only half an answer — the task is still sitting there. These are the three ways out, and they
    // reuse the existing task endpoints rather than adding a "resolve" concept the API doesn't need.
    //
    // Nothing here decides for the user. The app never silently reschedules or deletes a task; that
    // would be the same class of overreach as writing to their calendar without asking.

    /// Move the deadline forward to a real, near time so the task can compete again.
    func reschedule(taskId: String, to newDue: Date) async {
        struct DueUpdate: Encodable {
            let due_at: String
        }
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]
        do {
            let _: TaskPatchResponse = try await APIClient.shared.patch(
                "/api/v1/tasks/\(taskId)", body: DueUpdate(due_at: iso.string(from: newDue))
            )
        } catch {
            // fall through — the reload below keeps the UI honest either way
        }
        await load()
    }

    /// Drop the task entirely. Destructive, so the view confirms before calling this.
    func removeTask(taskId: String) async {
        try? await APIClient.shared.delete("/api/v1/tasks/\(taskId)")
        timers.stopIfTiming(taskId: taskId)
        await load()
    }

    private func maybePromptDuration(taskId: String, title: String,
                                     estimatedMinutes: Int?, measured: Int?) async {
        struct PromptResp: Decodable { let ask: Bool; let task_type: String? }
        guard let resp: PromptResp = try? await APIClient.shared.get(
            "/api/v1/tasks/\(taskId)/duration-prompt"
        ) else { return }

        // A measured duration is worth recording even once the assistant has stopped asking about
        // this type — it's free, and more observations only sharpen the estimate.
        if let measured, !resp.ask {
            await submitDuration(taskId: taskId, minutes: measured)
            return
        }
        guard resp.ask else { return }
        durationPrompt = DurationPrompt(
            id: taskId, title: title, estimatedMinutes: estimatedMinutes,
            taskType: resp.task_type, measuredMinutes: measured
        )
    }

    /// Record how long the task actually took → teaches the per-user estimate for its type.
    /// `taskType` carries a correction when the user says the detected type was wrong.
    func submitDuration(taskId: String, minutes: Int, taskType: String? = nil) async {
        struct Body: Encodable { let actual_minutes: Int; let task_type: String? }
        struct Resp: Decodable { let estimated_minutes: Int }
        let _: Resp? = try? await APIClient.shared.post(
            "/api/v1/tasks/\(taskId)/duration-feedback",
            body: Body(actual_minutes: minutes, task_type: taskType)
        )
        durationPrompt = nil
    }

    /// Lazily fetch the structured "Why This Recommendation?" explanation (only on tap).
    func fetchExplanation(taskId: String) async -> RecommendationExplanation? {
        return try? await APIClient.shared.get("/api/v1/now/why?task_id=\(taskId)")
    }

    /// User agrees this is the right next action — record it, then reveal Done/Snooze in place
    /// (no re-fetch; we stay on the same recommendation).
    func agree(taskId: String) async {
        await sendFeedback(taskId: taskId, signal: "agree", snoozeUntil: nil, reload: false)
    }

    /// User disagrees — record it (with an optional "why") and re-fetch so a different best action
    /// surfaces (the disagreed task is demoted, not hidden). The reason drives reason-based learning
    /// on the backend (TIME-271).
    func disagree(taskId: String, reason: String? = nil) async {
        await sendFeedback(taskId: taskId, signal: "disagree", snoozeUntil: nil, reason: reason)
    }

    /// Today's actionable tasks, for the "what would you rather do?" picker. Calendar meetings are
    /// filtered out — they're read-only blocks and aren't recommendable anyway (TIME-279/281).
    func swapCandidates(excluding taskId: String) async -> [TimelineTask] {
        let today = DateFormatter.swapPickerDay.string(from: Date())
        guard let entries: [TimelineEntry] = try? await APIClient.shared.get(
            "/api/v1/timeline/today/plan?date=\(today)"
        ) else { return [] }
        return entries.compactMap { entry -> TimelineTask? in
            guard !entry.isEvent, let task = entry.task else { return nil }
            guard task.id != taskId, task.status != "done", task.status != "cancelled" else { return nil }
            return task
        }
    }

    /// "Not that — this instead." Records the swap and pins the chosen task, then reloads so the
    /// user immediately sees their own choice as the recommendation (TIME-294/295).
    func swap(rejectedTaskId: String, chosenTaskId: String, reason: String?) async {
        guard case .loaded(let ctx) = uiState else { return }
        struct Body: Encodable {
            let rejected_task_id: String
            let chosen_task_id: String
            let reason: String?
            let recommendation_event_id: String?
        }
        struct Resp: Decodable { let id: String }
        let _: Resp? = try? await APIClient.shared.post(
            "/api/v1/recommendations/swap",
            body: Body(rejected_task_id: rejectedTaskId, chosen_task_id: chosenTaskId,
                       reason: reason, recommendation_event_id: ctx.recommendationEventId)
        )
        await load()
    }

    /// Snooze the current best task for a few hours; it drops out of Now until then.
    func snooze(taskId: String, hours: Int = 3) async {
        let until = ISO8601DateFormatter().string(from: Date().addingTimeInterval(Double(hours) * 3600))
        await sendFeedback(taskId: taskId, signal: "snooze", snoozeUntil: until)
    }

    /// Dismiss the current best task ("not now"); a different best task surfaces.
    func notNow(taskId: String) async {
        await sendFeedback(taskId: taskId, signal: "not_now", snoozeUntil: nil)
    }

    private func sendFeedback(taskId: String, signal: String, snoozeUntil: String?,
                              reason: String? = nil, reload: Bool = true) async {
        guard case .loaded(let ctx) = uiState else { return }
        struct FeedbackBody: Encodable {
            let task_id: String
            let signal: String
            let snooze_until: String?
            let reason: String?
            let recommendation_event_id: String?
        }
        do {
            let _: FeedbackResponse = try await APIClient.shared.post(
                "/api/v1/recommendations/feedback",
                body: FeedbackBody(task_id: taskId, signal: signal, snooze_until: snoozeUntil,
                                   reason: reason,
                                   recommendation_event_id: ctx.recommendationEventId)
            )
        } catch {
            // ignore; reload reflects the true state
        }
        if reload { await load() }
    }
}

// Minimal decodables for the mutation responses
private struct TaskPatchResponse: Decodable { let id: String }
private struct FeedbackResponse: Decodable { let id: String }


private extension DateFormatter {
    /// The device's local date, which is what the plan endpoint expects — the backend resolves the
    /// day in the user's stored timezone (TIME-283).
    static let swapPickerDay: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()
}
