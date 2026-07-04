import Foundation

struct TimelineTask: Decodable, Identifiable {
    let id: String
    let title: String
    let status: String
    let scheduledStart: Date?
    let scheduledEnd: Date?
    let estimatedMinutes: Int?
    let priority: Int

    enum CodingKeys: String, CodingKey {
        case id, title, status, priority
        case scheduledStart = "scheduled_start"
        case scheduledEnd = "scheduled_end"
        case estimatedMinutes = "estimated_minutes"
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

    func load() async {
        uiState = .loading
        do {
            let today = DateFormatter.shortDate.string(from: Date())
            let items: [TimelineTask] = try await APIClient.shared.get("/api/v1/timeline/today?date=\(today)")
            uiState = .loaded(items)
        } catch {
            uiState = .error(error.localizedDescription)
        }
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
