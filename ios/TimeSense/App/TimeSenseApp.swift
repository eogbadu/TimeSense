import SwiftUI
import UIKit

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
    // Default to the cosmic dark theme (the brand look); users can still switch in Settings.
    @AppStorage("appTheme") private var appTheme = "dark"

    init() {
        // Nav bar stays transparent (the cosmic background flows beneath the title). The title colour
        // adapts (UIColor.label = near-black on light, near-white on dark); the tab-bar background
        // flips navy↔light so no bar looks mismatched in either scheme.
        let nav = UINavigationBarAppearance()
        nav.configureWithTransparentBackground()
        nav.backgroundColor = .clear
        nav.titleTextAttributes = [.foregroundColor: UIColor.label]
        nav.largeTitleTextAttributes = [.foregroundColor: UIColor.label]
        UINavigationBar.appearance().standardAppearance = nav
        UINavigationBar.appearance().scrollEdgeAppearance = nav
        UINavigationBar.appearance().compactAppearance = nav

        let barBackground = UIColor { trait in
            trait.userInterfaceStyle == .dark
                ? UIColor(red: 0.031, green: 0.043, blue: 0.078, alpha: 1)   // Cosmic.base navy
                : UIColor.systemBackground
        }
        let tab = UITabBarAppearance()
        tab.configureWithOpaqueBackground()
        tab.backgroundColor = barBackground
        UITabBar.appearance().standardAppearance = tab
        UITabBar.appearance().scrollEdgeAppearance = tab
    }

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
