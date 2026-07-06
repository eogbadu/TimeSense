import Foundation
import WidgetKit

struct NowContext: Decodable {
    let greeting: String
    let usableMinutes: Int
    let bestTask: NowTask?
    let reason: String?
    let alternatives: [NowTask]?
    let moment: String?
    let feasibility: Feasibility?

    enum CodingKeys: String, CodingKey {
        case greeting
        case usableMinutes = "usable_minutes"
        case bestTask = "best_task"
        case reason
        case alternatives
        case moment
        case feasibility
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

    enum CodingKeys: String, CodingKey {
        case id, title, status, priority
        case estimatedMinutes = "estimated_minutes"
    }
}

struct DurationPrompt: Identifiable, Equatable {
    let id: String   // the completed task's id
    let title: String
}

enum NowUiState {
    case idle
    case loading
    case loaded(NowContext)
    case error(String)
}

@MainActor
final class NowViewModel: ObservableObject {
    @Published var uiState: NowUiState = .idle

    var context: NowContext? {
        if case .loaded(let c) = uiState { return c }
        return nil
    }

    func load() async {
        uiState = .loading
        do {
            let ctx: NowContext = try await APIClient.shared.get("/api/v1/now")
            uiState = .loaded(ctx)
            updateWidgetSnapshot(with: ctx)
        } catch {
            uiState = .error(error.localizedDescription)
        }
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

    /// Lazily fetch the "Why this?" explanation for a task (only when the user taps to expand).
    func fetchWhy(taskId: String) async -> String? {
        struct WhyResp: Decodable { let reason: String }
        let resp: WhyResp? = try? await APIClient.shared.get("/api/v1/now/why?task_id=\(taskId)")
        return resp?.reason
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
