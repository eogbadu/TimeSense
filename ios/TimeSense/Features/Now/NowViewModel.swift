import Foundation
import WidgetKit

struct NowContext: Decodable {
    let greeting: String
    let usableMinutes: Int
    let bestTask: NowTask?
    let reason: String?
    let alternatives: [NowTask]?

    enum CodingKeys: String, CodingKey {
        case greeting
        case usableMinutes = "usable_minutes"
        case bestTask = "best_task"
        case reason
        case alternatives
    }
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

    func markDone(taskId: String) async {
        guard case .loaded = uiState else { return }
        struct StatusUpdate: Encodable { let status: String }
        do {
            let _: TaskPatchResponse = try await APIClient.shared.patch(
                "/api/v1/tasks/\(taskId)", body: StatusUpdate(status: "done")
            )
            await load()
        } catch {
            // Reload anyway so UI stays consistent
            await load()
        }
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
