import Foundation

/// Where a tapped notification should take the user. Set by the AppDelegate on tap; observed by the
/// tab view (to switch tabs) and Today (to present the scheduler).
enum DeepRoute: Equatable {
    case now
    case scheduleTask(taskId: String, title: String)
}

@MainActor
final class DeepLinkRouter: ObservableObject {
    static let shared = DeepLinkRouter()
    @Published var route: DeepRoute?
}
