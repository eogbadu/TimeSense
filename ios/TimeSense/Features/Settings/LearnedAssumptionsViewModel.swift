import Foundation

struct RoutineAssumption: Decodable, Identifiable {
    let id: String
    let routineType: String
    let startMinute: Int
    let endMinute: Int
    let isCustomized: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case routineType = "routine_type"
        case startMinute = "start_minute"
        case endMinute = "end_minute"
        case isCustomized = "is_customized"
    }
}

enum LearnedAssumptionsUiState {
    case idle
    case loading
    case loaded([RoutineAssumption])
    case error(String)
}

/// A plain-language thing TimeSense has learned from your Agree/Disagree history.
struct LearnedPreference: Decodable, Identifiable {
    let kind: String            // prefers / avoids / avoids_at_time
    let label: String
    let detail: String
    let partOfDay: String?

    var id: String { "\(kind)-\(label)-\(partOfDay ?? "")" }

    enum CodingKeys: String, CodingKey {
        case kind, label, detail
        case partOfDay = "part_of_day"
    }
}

private struct LearnedPreferencesResponse: Decodable {
    let preferences: [LearnedPreference]
}

@MainActor
final class LearnedAssumptionsViewModel: ObservableObject {
    @Published var uiState: LearnedAssumptionsUiState = .idle
    @Published var preferences: [LearnedPreference] = []

    func load() async {
        uiState = .loading
        do {
            let routines: [RoutineAssumption] = try await APIClient.shared.get("/api/v1/routines")
            uiState = .loaded(routines)
        } catch {
            uiState = .error(error.localizedDescription)
        }
        // Additive + best-effort: a failure here must not block the routines screen.
        if let resp: LearnedPreferencesResponse = try? await APIClient.shared.get("/api/v1/recommendations/learned") {
            preferences = resp.preferences
        }
    }

    func update(routineType: String, startMinute: Int, endMinute: Int) async {
        struct Body: Encodable {
            let start_minute: Int
            let end_minute: Int
        }
        do {
            let updated: RoutineAssumption = try await APIClient.shared.patch(
                "/api/v1/routines/\(routineType)",
                body: Body(start_minute: startMinute, end_minute: endMinute)
            )
            guard case .loaded(var routines) = uiState,
                  let index = routines.firstIndex(where: { $0.routineType == routineType }) else {
                await load()
                return
            }
            routines[index] = updated
            uiState = .loaded(routines)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }
}
