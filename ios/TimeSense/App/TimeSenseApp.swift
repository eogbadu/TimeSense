import SwiftUI
import FirebaseCore

@main
struct TimeSenseApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var authService = AuthService()

    init() {
        FirebaseApp.configure()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .environmentObject(authService)
                .onAppear {
                    appState.bind(to: authService)
                }
        }
    }
}
