import SwiftUI
import Combine

final class AppState: ObservableObject {
    @Published var isAuthenticated: Bool = false
    @Published var isPremium: Bool = false
    @Published var isNewUser: Bool = false
    @Published var selectedTab: Tab = .now

    private var cancellables = Set<AnyCancellable>()

    @MainActor
    func bind(to authService: AuthService) {
        authService.$currentUser
            .receive(on: RunLoop.main)
            .sink { [weak self] user in
                guard let self else { return }
                self.isAuthenticated = user != nil
                if user != nil {
                    Task { await self.refreshEntitlement() }
                } else {
                    self.isPremium = false
                }
            }
            .store(in: &cancellables)
    }

    /// Load the user's real Premium entitlement (active subscription or the 14-day intro trial).
    /// Called on sign-in; leaves `isPremium` unchanged on a transient failure.
    @MainActor
    func refreshEntitlement() async {
        do {
            let ent: Entitlement = try await APIClient.shared.get("/api/v1/subscriptions/me/entitlement")
            isPremium = ent.isPremium
        } catch {
            // Keep the last known value on network error rather than downgrading the user.
        }
    }

    enum Tab: Int, CaseIterable {
        case now, today, capture, insights, settings
    }
}

/// Premium entitlement from GET /api/v1/subscriptions/me/entitlement.
private struct Entitlement: Decodable {
    let isPremium: Bool

    enum CodingKeys: String, CodingKey {
        case isPremium = "is_premium"
    }
}
