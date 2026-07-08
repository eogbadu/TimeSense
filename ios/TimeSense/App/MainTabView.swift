import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var appState: AppState
    @ObservedObject private var router = DeepLinkRouter.shared

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
        // Route notification taps to the right tab. Today clears .scheduleTask after presenting the
        // scheduler; we clear .now here.
        .onChange(of: router.route) { _, route in
            switch route {
            case .scheduleTask:
                appState.selectedTab = .today
            case .now:
                appState.selectedTab = .now
                router.route = nil
            case .none:
                break
            }
        }
    }
}
