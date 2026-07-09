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

    enum CodingKeys: String, CodingKey {
        case nextEventTitle = "next_event_title"
        case nextEventAt = "next_event_at"
        case nextEventInMinutes = "next_event_in_minutes"
        case tasksDueToday = "tasks_due_today"
        case tasksCompletedToday = "tasks_completed_today"
        case energyLevel = "energy_level"
        case sleepHours = "sleep_hours"
        case currentPlace = "current_place"
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

    func markDone(taskId: String, title: String) async {
        guard case .loaded = uiState else { return }
        struct StatusUpdate: Encodable { let status: String }
        do {
            let _: TaskPatchResponse = try await APIClient.shared.patch(
                "/api/v1/tasks/\(taskId)", body: StatusUpdate(status: "done")
            )
            await maybePromptDuration(taskId: taskId, title: title)
            await load()
        } catch {
            // Reload anyway so UI stays consistent
            await load()
        }
    }

    private func maybePromptDuration(taskId: String, title: String) async {
        struct PromptResp: Decodable { let ask: Bool }
        if let resp: PromptResp = try? await APIClient.shared.get(
            "/api/v1/tasks/\(taskId)/duration-prompt"
        ), resp.ask {
            durationPrompt = DurationPrompt(id: taskId, title: title)
        }
    }

    /// Record how long the task actually took → teaches the per-user estimate.
    func submitDuration(taskId: String, minutes: Int) async {
        struct Body: Encodable { let actual_minutes: Int }
        struct Resp: Decodable { let estimated_minutes: Int }
        let _: Resp? = try? await APIClient.shared.post(
            "/api/v1/tasks/\(taskId)/duration-feedback", body: Body(actual_minutes: minutes)
        )
        durationPrompt = nil
    }

    /// Lazily fetch the structured "Why This Recommendation?" explanation (only on tap).
    func fetchExplanation(taskId: String) async -> RecommendationExplanation? {
        return try? await APIClient.shared.get("/api/v1/now/why?task_id=\(taskId)")
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

    private func sendFeedback(taskId: String, signal: String, snoozeUntil: String?) async {
        guard case .loaded = uiState else { return }
        struct FeedbackBody: Encodable {
            let task_id: String
            let signal: String
            let snooze_until: String?
        }
        do {
            let _: FeedbackResponse = try await APIClient.shared.post(
                "/api/v1/recommendations/feedback",
                body: FeedbackBody(task_id: taskId, signal: signal, snooze_until: snoozeUntil)
            )
        } catch {
            // ignore; reload reflects the true state
        }
        await load()
    }
}

// Minimal decodables for the mutation responses
private struct TaskPatchResponse: Decodable { let id: String }
private struct FeedbackResponse: Decodable { let id: String }
