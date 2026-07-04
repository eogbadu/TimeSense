import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        TabView(selection: $appState.selectedTab) {
            NowView()
                .tabItem {
                    Label("Now", systemImage: "sparkles")
                }
                .tag(AppState.Tab.now)

            TodayView()
                .tabItem {
                    Label("Today", systemImage: "calendar")
                }
                .tag(AppState.Tab.today)

            CaptureView()
                .tabItem {
                    Label("Capture", systemImage: "plus.circle.fill")
                }
                .tag(AppState.Tab.capture)

            InsightsView()
                .tabItem {
                    Label("Insights", systemImage: "chart.bar.fill")
                }
                .tag(AppState.Tab.insights)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
                .tag(AppState.Tab.settings)
        }
        .tint(DesignTokens.Color.accent)
    }
}
