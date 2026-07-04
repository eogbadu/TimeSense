import SwiftUI
#if canImport(FirebaseCore)
import FirebaseCore
#endif

@main
struct TimeSenseApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var authService = AuthService()

    init() {
        #if canImport(FirebaseCore)
        FirebaseApp.configure()
        #endif
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
