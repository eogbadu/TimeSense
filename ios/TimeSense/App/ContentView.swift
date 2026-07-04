import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var authService: AuthService

    var body: some View {
        Group {
            if appState.isAuthenticated {
                if appState.isNewUser {
                    OnboardingView {
                        appState.isNewUser = false
                    }
                } else {
                    MainTabView()
                }
            } else {
                SignInView()
            }
        }
        .animation(DesignTokens.Animation.standard, value: appState.isAuthenticated)
    }
}
