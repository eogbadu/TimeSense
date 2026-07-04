import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        if appState.isAuthenticated {
            MainTabView()
        } else {
            // Placeholder — auth flow added in TIME-020
            MainTabView()
        }
    }
}
