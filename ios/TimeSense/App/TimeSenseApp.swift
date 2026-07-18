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
        // At the top (scroll edge) the nav bar is transparent so the cosmic background flows behind the
        // title; once you scroll, it gains a subtle adaptive material so content stops sliding under the
        // fixed title. Title colour adapts (UIColor.label). Tab-bar background flips navy↔light.
        let titleAttrs: [NSAttributedString.Key: Any] = [.foregroundColor: UIColor.label]

        let atEdge = UINavigationBarAppearance()
        atEdge.configureWithTransparentBackground()
        atEdge.backgroundColor = .clear
        atEdge.titleTextAttributes = titleAttrs
        atEdge.largeTitleTextAttributes = titleAttrs

        let scrolled = UINavigationBarAppearance()
        scrolled.configureWithDefaultBackground()   // adaptive system material (blurred, light/dark aware)
        scrolled.titleTextAttributes = titleAttrs
        scrolled.largeTitleTextAttributes = titleAttrs

        UINavigationBar.appearance().scrollEdgeAppearance = atEdge
        UINavigationBar.appearance().standardAppearance = scrolled
        UINavigationBar.appearance().compactAppearance = scrolled

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
