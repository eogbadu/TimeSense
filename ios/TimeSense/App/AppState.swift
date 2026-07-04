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
                self?.isAuthenticated = user != nil
            }
            .store(in: &cancellables)
    }

    enum Tab: Int, CaseIterable {
        case now, today, capture, insights, settings
    }
}
