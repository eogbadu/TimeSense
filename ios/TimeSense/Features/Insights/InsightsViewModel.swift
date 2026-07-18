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

// MARK: - Chart series (TIME-274)

/// Shared UTC parser for the `yyyy-MM-dd` date strings the series endpoints return.
private let ymdFormatter: DateFormatter = {
    let f = DateFormatter()
    f.dateFormat = "yyyy-MM-dd"
    f.locale = Locale(identifier: "en_US_POSIX")
    f.timeZone = TimeZone(identifier: "UTC")
    return f
}()

func parseYMD(_ s: String) -> Date { ymdFormatter.date(from: s) ?? Date() }

/// One week of weekly-insight history, adapted for the trend charts (GET /insights/history).
struct WeeklyTrendPoint: Identifiable {
    let weekStart: Date
    let tasksCompleted: Int
    let tasksTotal: Int
    let completionPct: Double?      // 0–100
    let acceptancePct: Double?      // 0–100
    let confidencePct: Double?      // 0–100
    var id: Date { weekStart }
}

/// Daily steps + exercise minutes (GET /insights/activity).
struct DailyActivityPoint: Decodable, Identifiable {
    let day: String
    let steps: Int
    let exerciseMinutes: Int
    var id: String { day }
    var date: Date { parseYMD(day) }
    enum CodingKeys: String, CodingKey { case day, steps, exerciseMinutes = "exercise_minutes" }
}
private struct ActivitySeriesResponse: Decodable { let points: [DailyActivityPoint] }

/// Per-week running miles + workout counts (GET /insights/workouts).
struct WeeklyWorkoutPoint: Decodable, Identifiable {
    let weekStart: String
    let runningMiles: Double
    let runningCount: Int
    let totalCount: Int
    var id: String { weekStart }
    var date: Date { parseYMD(weekStart) }
    enum CodingKeys: String, CodingKey {
        case weekStart = "week_start"
        case runningMiles = "running_miles"
        case runningCount = "running_count"
        case totalCount = "total_count"
    }
}
private struct WorkoutSeriesResponse: Decodable { let points: [WeeklyWorkoutPoint] }

/// Average steps by hour-of-day, the sit-vs-move profile (GET /insights/hourly).
struct HourlyStepsPoint: Decodable, Identifiable {
    let hour: Int
    let avgSteps: Int
    var id: Int { hour }
    enum CodingKeys: String, CodingKey { case hour, avgSteps = "avg_steps" }
}
private struct HourlySeriesResponse: Decodable { let points: [HourlyStepsPoint]; let days: Int }

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
    @Published var trends: [WeeklyTrendPoint] = []
    @Published var activity: [DailyActivityPoint] = []
    @Published var workouts: [WeeklyWorkoutPoint] = []
    @Published var hourly: [HourlyStepsPoint] = []

    func load() async {
        uiState = .loading
        // Behavioral patterns are best-effort — a failure here shouldn't blank the weekly insight.
        if let resp: BehavioralPatternsResponse = try? await APIClient.shared.get("/api/v1/insights/patterns") {
            patterns = resp.patterns
        }
        await loadChartSeries()
        do {
            let insight: WeeklyInsight = try await APIClient.shared.get("/api/v1/insights/weekly")
            uiState = .loaded(insight)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }

    /// All chart series are best-effort and independent — a missing one just hides its card.
    private func loadChartSeries() async {
        if let history: [WeeklyInsight] = try? await APIClient.shared.get("/api/v1/insights/history?limit=8") {
            // History comes newest-first; charts read left-to-right oldest-first.
            trends = history.reversed().map {
                WeeklyTrendPoint(
                    weekStart: parseYMD($0.weekStart),
                    tasksCompleted: $0.tasksCompleted,
                    tasksTotal: $0.tasksTotal,
                    completionPct: $0.completionRate.map { $0 * 100 },
                    acceptancePct: $0.recommendationAcceptanceRate.map { $0 * 100 },
                    confidencePct: $0.meanConfidence.map { $0 * 100 }
                )
            }
        }
        if let a: ActivitySeriesResponse = try? await APIClient.shared.get("/api/v1/insights/activity?days=30") {
            activity = a.points
        }
        if let w: WorkoutSeriesResponse = try? await APIClient.shared.get("/api/v1/insights/workouts?weeks=8") {
            workouts = w.points
        }
        if let h: HourlySeriesResponse = try? await APIClient.shared.get("/api/v1/insights/hourly?days=7") {
            hourly = h.points
        }
    }
}
