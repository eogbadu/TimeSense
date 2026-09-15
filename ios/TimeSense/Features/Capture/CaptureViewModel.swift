import Foundation

/// One step of a group that a capture created (TIME-329).
struct CapturedStep: Decodable, Equatable, Identifiable {
    let id: String
    let title: String
    let estimatedMinutes: Int?
    let blockedBy: [TaskRef]?

    enum CodingKeys: String, CodingKey {
        case id, title
        case estimatedMinutes = "estimated_minutes"
        case blockedBy = "blocked_by"
    }
}

struct CapturedTask: Decodable, Equatable {
    let id: String
    let title: String
    let status: String
    let priority: Int
    let estimatedMinutes: Int?
    let scheduledStart: Date?
    let scheduledEnd: Date?
    let dueAt: Date?
    let autoScheduled: Bool
    let source: String
    // What the capture joined or created (TIME-329). Optional with defaults, so an older response still
    // decodes.
    var parentTaskId: String? = nil
    var parentTitle: String? = nil
    var steps: [CapturedStep]? = nil
    /// An open task this looks like part of. Offered with one tap, never applied by itself.
    var suggestedParent: TaskRef? = nil

    enum CodingKeys: String, CodingKey {
        case id, title, status, priority, source, steps
        case estimatedMinutes = "estimated_minutes"
        case scheduledStart = "scheduled_start"
        case scheduledEnd = "scheduled_end"
        case dueAt = "due_at"
        case autoScheduled = "auto_scheduled"
        case parentTaskId = "parent_task_id"
        case parentTitle = "parent_title"
        case suggestedParent = "suggested_parent"
    }

    var capturedSteps: [CapturedStep] { steps ?? [] }
}

private struct CaptureRequest: Encodable {
    let rawInput: String
    let userTimezone: String
    let typeHint: String?
    let scheduledAt: Date?
    let dueAt: Date?
    let locationName: String?
    let locationLat: Double?
    let locationLng: Double?
    /// The "Part of…" chip. It wins over anything the words themselves suggest (TIME-325/329).
    let parentTaskId: String?

    enum CodingKeys: String, CodingKey {
        case rawInput = "raw_input"
        case userTimezone = "user_timezone"
        case typeHint = "type_hint"
        case scheduledAt = "scheduled_at"
        case dueAt = "due_at"
        case locationName = "location_name"
        case locationLat = "location_lat"
        case locationLng = "location_lng"
        case parentTaskId = "parent_task_id"
    }
}

extension StepLabels {
    /// What a new capture can be "Part of…": today's open tasks that aren't steps themselves.
    static func captureParentCandidates(in entries: [TimelineEntry]) -> [TimelineTask] {
        entries.compactMap(\.task).filter { $0.parentTaskId == nil && isOpen($0) }
    }
}

/// A result from /places/search — a saved place or a maps match.
struct PlaceSearchResult: Decodable, Identifiable, Equatable {
    let name: String
    let address: String?
    let latitude: Double
    let longitude: Double
    let source: String   // "saved" | "maps"
    var id: String { "\(source)-\(name)-\(latitude)-\(longitude)" }
}

enum CaptureUiState: Equatable {
    case idle
    case loading
    case success(title: String)
    case error(String)
}

@MainActor
final class CaptureViewModel: ObservableObject {
    @Published var uiState: CaptureUiState = .idle
    /// The most recent capture — drives the "TimeSense detected" results shown after a capture.
    /// Cleared on reset, returning the section to its idle capability tiles.
    @Published private(set) var lastCaptured: CapturedTask?

    private let api = APIClient.shared

    @Published var placeResults: [PlaceSearchResult] = []

    // MARK: - Groups (TIME-329)

    /// The task chosen with the "Part of…" chip for the next capture.
    @Published var partOf: TimelineTask?
    /// Today's plan, loaded when the chip is opened, for its picker.
    @Published private(set) var planEntries: [TimelineEntry] = []
    /// "Before Fill out the form?", offered after a capture joins a group whose steps are in order.
    @Published private(set) var placeOffer: TaskRef?
    /// The user said no to "Part of X?".
    @Published var suggestionDismissed = false
    /// A follow-up the server refused (Undo, joining, placing), in the server's own words.
    @Published private(set) var followUpError: String?

    func searchPlaces(_ query: String, near: (lat: Double, lng: Double)?) async {
        let q = query.trimmingCharacters(in: .whitespaces)
        guard q.count >= 2 else { placeResults = []; return }
        let enc = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? q
        var path = "/api/v1/places/search?q=\(enc)"
        if let near { path += "&lat=\(near.lat)&lng=\(near.lng)" }
        placeResults = (try? await api.get(path)) ?? []
    }

    func loadPlanForPicker() async {
        let today = DateFormatter.capturePlanDay.string(from: Date())
        planEntries = (try? await api.get("/api/v1/timeline/today/plan?date=\(today)")) ?? []
    }

    func submit(
        rawInput: String, typeHint: String? = nil,
        scheduledAt: Date? = nil, dueAt: Date? = nil, location: PlaceSearchResult? = nil
    ) async {
        guard !rawInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        uiState = .loading
        let timezone = TimeZone.current.identifier
        do {
            let task: CapturedTask = try await api.post(
                "/api/v1/capture",
                body: CaptureRequest(
                    rawInput: rawInput, userTimezone: timezone, typeHint: typeHint,
                    scheduledAt: scheduledAt, dueAt: dueAt,
                    locationName: location?.name, locationLat: location?.latitude,
                    locationLng: location?.longitude,
                    parentTaskId: partOf?.id
                )
            )
            lastCaptured = task
            partOf = nil
            placeOffer = nil
            suggestionDismissed = false
            followUpError = nil
            uiState = .success(title: task.title)
            if task.parentTaskId != nil { await offerPlace(for: task) }
        } catch let error as APIError {
            // A refused chip ("That task is already finished.") is worth saying in the server's words.
            uiState = .error(StepLabels.message(for: error) == "That didn't work. Please try again."
                             ? (error.localizedDescription ?? "Capture failed.")
                             : StepLabels.message(for: error))
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }

    /// "Undo" on "Added to X": the capture stays, as a task of its own.
    func undoJoin() async {
        guard let task = lastCaptured else { return }
        placeOffer = nil
        await followUp {
            let _: IDOnlyResponse = try await api.patch("/api/v1/tasks/\(task.id)", body: LeaveGroup())
        }
    }

    /// One tap on "Part of X?": join the suggested task.
    func acceptSuggestion() async {
        guard let task = lastCaptured, let parent = task.suggestedParent else { return }
        struct Body: Encodable { let parent_task_id: String }
        await followUp {
            let _: IDOnlyResponse = try await api.patch(
                "/api/v1/tasks/\(task.id)", body: Body(parent_task_id: parent.id)
            )
        }
        if let joined = lastCaptured, joined.parentTaskId != nil { await offerPlace(for: joined) }
    }

    /// "Yes" to "Before …?": move the step there. Positions shift as a group changes, so the target's
    /// position is read from the plan as it is now.
    func acceptPlace() async {
        guard let task = lastCaptured, let before = placeOffer else { return }
        placeOffer = nil
        await loadPlanForPicker()
        guard let position = StepLabels.findTask(before.id, in: planEntries)?.position else { return }
        struct Body: Encodable { let position: Int }
        await followUp {
            let _: IDOnlyResponse = try await api.patch("/api/v1/tasks/\(task.id)", body: Body(position: position))
        }
    }

    func declinePlace() { placeOffer = nil }

    func reset() {
        uiState = .idle
        lastCaptured = nil
        placeOffer = nil
        suggestionDismissed = false
        followUpError = nil
    }

    private func offerPlace(for task: CapturedTask) async {
        guard let parentId = task.parentTaskId else { return }
        struct Resp: Decodable {
            let before_step_id: String?
            let before_step_title: String?
        }
        if let resp: Resp = try? await api.get("/api/v1/tasks/\(task.id)/step-position?parent_id=\(parentId)"),
           let id = resp.before_step_id, let title = resp.before_step_title {
            placeOffer = TaskRef(id: id, title: title)
        }
    }

    /// Run a follow-up change, then show the captured task as it now is.
    private func followUp(_ change: () async throws -> Void) async {
        guard let task = lastCaptured else { return }
        followUpError = nil
        do {
            try await change()
            if let fresh: CapturedTask = try? await api.get("/api/v1/tasks/\(task.id)") {
                lastCaptured = fresh
            }
        } catch {
            followUpError = StepLabels.message(for: error)
        }
    }
}

private struct IDOnlyResponse: Decodable { let id: String }

private extension DateFormatter {
    /// The device's local date, which the plan endpoint expects (TIME-283).
    static let capturePlanDay: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()
}
