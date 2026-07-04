import SwiftUI

final class AppState: ObservableObject {
    @Published var isAuthenticated: Bool = false
    @Published var isPremium: Bool = false
    @Published var selectedTab: Tab = .now

    enum Tab: Int, CaseIterable {
        case now, today, capture, insights, settings
    }
}
