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
    let recommendationsShown: Int
    let recommendationsAccepted: Int
    let recommendationAcceptanceRate: Double?
    let meanConfidence: Double?
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
        case recommendationsShown = "recommendations_shown"
        case recommendationsAccepted = "recommendations_accepted"
        case recommendationAcceptanceRate = "recommendation_acceptance_rate"
        case meanConfidence = "mean_confidence"
        case summaryText = "summary_text"
    }
}

/// A behavioral pattern from Apple Health + commutes (GET /insights/patterns).
struct BehavioralPattern: Decodable, Identifiable {
    let category: String   // workouts | movement | driving
    let icon: String       // SF Symbol name
    let title: String
    let detail: String

    var id: String { "\(category)-\(title)" }
}

private struct BehavioralPatternsResponse: Decodable {
    let patterns: [BehavioralPattern]
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
    @Published var patterns: [BehavioralPattern] = []

    func load() async {
        uiState = .loading
        // Behavioral patterns are best-effort — a failure here shouldn't blank the weekly insight.
        if let resp: BehavioralPatternsResponse = try? await APIClient.shared.get("/api/v1/insights/patterns") {
            patterns = resp.patterns
        }
        do {
            let insight: WeeklyInsight = try await APIClient.shared.get("/api/v1/insights/weekly")
            uiState = .loaded(insight)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }
}
