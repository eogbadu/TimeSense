import Foundation

struct WeeklyInsight: Decodable {
    let weekStart: String
    let weekEnd: String
    let tasksCompleted: Int
    let tasksTotal: Int
    let completionRate: Double?
    let mostSkippedMeal: String?
    let lateWakeCount: Int
    let commuteConfirmedCount: Int
    let feedbackDoneCount: Int
    let feedbackNotNowCount: Int
    let summaryText: String

    enum CodingKeys: String, CodingKey {
        case weekStart = "week_start"
        case weekEnd = "week_end"
        case tasksCompleted = "tasks_completed"
        case tasksTotal = "tasks_total"
        case completionRate = "completion_rate"
        case mostSkippedMeal = "most_skipped_meal"
        case lateWakeCount = "late_wake_count"
        case commuteConfirmedCount = "commute_confirmed_count"
        case feedbackDoneCount = "feedback_done_count"
        case feedbackNotNowCount = "feedback_not_now_count"
        case summaryText = "summary_text"
    }
}

enum InsightsUiState {
    case idle
    case loading
    case loaded(WeeklyInsight)
    case error(String)
}

@MainActor
final class InsightsViewModel: ObservableObject {
    @Published var uiState: InsightsUiState = .idle

    func load() async {
        uiState = .loading
        do {
            let insight: WeeklyInsight = try await APIClient.shared.get("/api/v1/insights/weekly")
            uiState = .loaded(insight)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }
}
