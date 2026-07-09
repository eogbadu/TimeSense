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

    enum CodingKeys: String, CodingKey {
        case rawInput = "raw_input"
        case userTimezone = "user_timezone"
        case typeHint = "type_hint"
    }
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

    func submit(rawInput: String, typeHint: String? = nil) async {
        guard !rawInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        uiState = .loading
        let timezone = TimeZone.current.identifier
        do {
            let task: CapturedTask = try await api.post(
                "/api/v1/capture",
                body: CaptureRequest(rawInput: rawInput, userTimezone: timezone, typeHint: typeHint)
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
