import SwiftUI
#if canImport(FirebaseCore)
import FirebaseCore
#endif

@main
struct TimeSenseApp: App {
    // Handles Firebase configure + LocationService init on launch (incl. background relaunch from a
    // geofence event).
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var appState = AppState()
    @StateObject private var authService = AuthService()
    @AppStorage("appTheme") private var appTheme = "system"

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .environmentObject(authService)
                .preferredColorScheme(colorScheme)
                .onAppear {
                    appState.bind(to: authService)
                }
        }
    }

    private var colorScheme: ColorScheme? {
        switch appTheme {
        case "light": return .light
        case "dark": return .dark
        default: return nil   // follow the system
        }
    }
}
