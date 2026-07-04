import Foundation

struct NowContext: Decodable {
    let greeting: String
    let usableMinutes: Int
    let bestTask: NowTask?

    enum CodingKeys: String, CodingKey {
        case greeting
        case usableMinutes = "usable_minutes"
        case bestTask = "best_task"
    }
}

struct NowTask: Decodable, Identifiable {
    let id: String
    let title: String
    let status: String
    let estimatedMinutes: Int?
    let priority: Int

    enum CodingKeys: String, CodingKey {
        case id, title, status, priority
        case estimatedMinutes = "estimated_minutes"
    }
}

enum NowUiState {
    case idle
    case loading
    case loaded(NowContext)
    case error(String)
}

@MainActor
final class NowViewModel: ObservableObject {
    @Published var uiState: NowUiState = .idle

    var context: NowContext? {
        if case .loaded(let c) = uiState { return c }
        return nil
    }

    func load() async {
        uiState = .loading
        do {
            let ctx: NowContext = try await APIClient.shared.get("/api/v1/now")
            uiState = .loaded(ctx)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }

    func markDone(taskId: String) async {
        guard case .loaded = uiState else { return }
        struct StatusUpdate: Encodable { let status: String }
        do {
            let _: TaskPatchResponse = try await APIClient.shared.patch(
                "/api/v1/tasks/\(taskId)", body: StatusUpdate(status: "done")
            )
            await load()
        } catch {
            // Reload anyway so UI stays consistent
            await load()
        }
    }
}

// Minimal decodable for the PATCH response
private struct TaskPatchResponse: Decodable { let id: String }
