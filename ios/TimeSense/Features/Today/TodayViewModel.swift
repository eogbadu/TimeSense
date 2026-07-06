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

enum TodayUiState {
    case idle
    case loading
    case loaded([TimelineTask])
    case error(String)
}

@MainActor
final class TodayViewModel: ObservableObject {
    @Published var uiState: TodayUiState = .idle

    var tasks: [TimelineTask] {
        if case .loaded(let items) = uiState { return items }
        return []
    }

    var doneCount: Int { tasks.filter { $0.status == "done" }.count }

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
            let items: [TimelineTask] = try await APIClient.shared.get("/api/v1/timeline/today?date=\(today)")
            uiState = .loaded(items)
            updateWidgetSnapshot(with: items)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }

    /// Updates only nextEvent, preserving whatever NowViewModel last wrote for
    /// usableMinutes/bestTask, then asks WidgetKit to refresh.
    private func updateWidgetSnapshot(with items: [TimelineTask]) {
        let now = Date()
        let upcoming: [(task: TimelineTask, start: Date)] = items
            .filter { $0.status != "done" }
            .compactMap { task in
                guard let start = task.scheduledStart else { return nil }
                let end = task.scheduledEnd ?? start
                guard end >= now else { return nil }
                return (task, start)
            }
        let next = upcoming.min { $0.start < $1.start }

        var snapshot = WidgetSnapshot.load() ?? .empty
        snapshot.nextEvent = next.map { entry in
            WidgetSnapshot.Event(title: entry.task.title, start: entry.start, end: entry.task.scheduledEnd)
        }
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
