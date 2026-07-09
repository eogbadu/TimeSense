import Foundation

struct CapturedTask: Decodable {
    let id: String
    let title: String
    let status: String
    let estimatedMinutes: Int?
    let dueAt: Date?
    let source: String

    enum CodingKeys: String, CodingKey {
        case id, title, status, source
        case estimatedMinutes = "estimated_minutes"
        case dueAt = "due_at"
    }
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

    enum CodingKeys: String, CodingKey {
        case rawInput = "raw_input"
        case userTimezone = "user_timezone"
        case typeHint = "type_hint"
        case scheduledAt = "scheduled_at"
        case dueAt = "due_at"
        case locationName = "location_name"
        case locationLat = "location_lat"
        case locationLng = "location_lng"
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

    private let api = APIClient.shared

    @Published var placeResults: [PlaceSearchResult] = []

    func searchPlaces(_ query: String, near: (lat: Double, lng: Double)?) async {
        let q = query.trimmingCharacters(in: .whitespaces)
        guard q.count >= 2 else { placeResults = []; return }
        let enc = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? q
        var path = "/api/v1/places/search?q=\(enc)"
        if let near { path += "&lat=\(near.lat)&lng=\(near.lng)" }
        placeResults = (try? await api.get(path)) ?? []
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
                    locationLng: location?.longitude
                )
            )
            uiState = .success(title: task.title)
        } catch let error as APIError {
            uiState = .error(error.localizedDescription ?? "Capture failed.")
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }

    func reset() {
        uiState = .idle
    }
}
