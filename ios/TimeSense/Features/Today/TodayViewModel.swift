import Foundation
import WidgetKit

struct TimelineTask: Decodable, Identifiable {
    let id: String
    let title: String
    let status: String
    let scheduledStart: Date?
    let scheduledEnd: Date?
    let estimatedMinutes: Int?
    let priority: Int
    let autoScheduled: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, status, priority
        case scheduledStart = "scheduled_start"
        case scheduledEnd = "scheduled_end"
        case estimatedMinutes = "estimated_minutes"
        case autoScheduled = "auto_scheduled"
    }
}

/// One row of the unified Smart Plan: an actionable `task`, or a read-only calendar `event` block.
struct TimelineEntry: Decodable, Identifiable {
    let kind: String            // "task" | "event"
    let id: String
    let title: String
    let start: Date?
    let end: Date?
    let location: String?
    let task: TimelineTask?     // present when kind == "task"

    var isEvent: Bool { kind == "event" }
}

enum TodayUiState {
    case idle
    case loading
    case loaded([TimelineEntry])
    case error(String)
}

@MainActor
final class TodayViewModel: ObservableObject {
    @Published var uiState: TodayUiState = .idle
    /// The current best-next-action (same as Now) — shown in the "AI Recommended Now" card.
    @Published var recommendation: NowContext?

    var entries: [TimelineEntry] {
        if case .loaded(let items) = uiState { return items }
        return []
    }

    /// Just the actionable task entries (calendar events are read-only and don't count toward totals).
    var tasks: [TimelineTask] { entries.compactMap { $0.task } }

    var doneCount: Int { tasks.filter { $0.status == "done" }.count }

    /// Lazily fetch the structured explanation for the recommended task.
    func fetchExplanation(taskId: String) async -> RecommendationExplanation? {
        return try? await APIClient.shared.get("/api/v1/now/why?task_id=\(taskId)")
    }

    func markDone(taskId: String) async {
        struct StatusUpdate: Encodable { let status: String }
        struct Resp: Decodable { let id: String }
        let _: Resp? = try? await APIClient.shared.patch(
            "/api/v1/tasks/\(taskId)", body: StatusUpdate(status: "done")
        )
        await load()
    }

    /// Delete a task that's completed or no longer viable (soft-delete on the backend).
    func deleteTask(taskId: String) async {
        try? await APIClient.shared.delete("/api/v1/tasks/\(taskId)")
        await load()
    }

    /// Ask the engine for the earliest free block (avoiding calendar events + scheduled tasks). Falls
    /// back to "now + duration" if nothing fits today.
    func suggestedSlot(taskId: String, estimatedMinutes: Int?) async -> (start: Date, end: Date) {
        struct Resp: Decodable { let fits: Bool; let start: Date?; let end: Date? }
        let resp: Resp? = try? await APIClient.shared.get("/api/v1/tasks/\(taskId)/suggested-slot")
        if let resp, resp.fits, let s = resp.start, let e = resp.end {
            return (s, e)
        }
        let start = Date()
        return (start, start.addingTimeInterval(TimeInterval((estimatedMinutes ?? 30) * 60)))
    }

    /// Undo an auto-placed time — the task becomes untimed again.
    func unschedule(taskId: String) async {
        struct Empty: Encodable {}
        struct TaskResp: Decodable { let id: String }
        let _: TaskResp? = try? await APIClient.shared.post(
            "/api/v1/tasks/\(taskId)/unschedule", body: Empty()
        )
        await load()
    }

    func load() async {
        uiState = .loading
        do {
            let today = DateFormatter.shortDate.string(from: Date())
            let items: [TimelineEntry] = try await APIClient.shared.get("/api/v1/timeline/today/plan?date=\(today)")
            recommendation = try? await APIClient.shared.get("/api/v1/now")
            uiState = .loaded(items)
            updateWidgetSnapshot(with: items)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }

    /// Updates only nextEvent (a task OR a calendar meeting, whichever is soonest), preserving whatever
    /// NowViewModel last wrote for usableMinutes/bestTask, then asks WidgetKit to refresh.
    private func updateWidgetSnapshot(with items: [TimelineEntry]) {
        let now = Date()
        let upcoming: [(title: String, start: Date, end: Date?)] = items
            .filter { $0.task?.status != "done" }   // done tasks skip; events have no status
            .compactMap { entry in
                guard let start = entry.start else { return nil }
                let end = entry.end ?? start
                guard end >= now else { return nil }
                return (entry.title, start, entry.end)
            }
        let next = upcoming.min { $0.start < $1.start }

        var snapshot = WidgetSnapshot.load() ?? .empty
        snapshot.nextEvent = next.map { WidgetSnapshot.Event(title: $0.title, start: $0.start, end: $0.end) }
        snapshot.updatedAt = Date()
        snapshot.save()
        WidgetCenter.shared.reloadAllTimelines()
    }

    func visualState(for task: TimelineTask) -> TimelineVisualState {
        let now = Date()
        if task.status == "done" { return .done }
        if let end = task.scheduledEnd, end < now { return .past }
        if let start = task.scheduledStart, let end = task.scheduledEnd,
           start <= now && now <= end { return .current }
        if let start = task.scheduledStart, start <= now && task.scheduledEnd == nil { return .current }
        return .future
    }
}

enum TimelineVisualState { case past, current, future, done }

private extension DateFormatter {
    static let shortDate: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()
}
