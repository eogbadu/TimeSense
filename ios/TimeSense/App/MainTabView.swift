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
        // Swipe horizontally to move between tabs (in addition to tapping the bar). Low-priority +
        // predominantly-horizontal + distance-thresholded so it doesn't fight vertical scrolling or
        // Today's row swipe-to-reveal (a child gesture on a row wins over this parent gesture).
        .gesture(
            DragGesture(minimumDistance: 30, coordinateSpace: .local)
                .onEnded { value in
                    let dx = value.translation.width, dy = value.translation.height
                    guard abs(dx) > 80, abs(dx) > abs(dy) * 1.6 else { return }
                    let tabs = AppState.Tab.allCases
                    guard let i = tabs.firstIndex(of: appState.selectedTab) else { return }
                    if dx < 0, i < tabs.count - 1 {
                        withAnimation(DesignTokens.Animation.standard) { appState.selectedTab = tabs[i + 1] }
                    } else if dx > 0, i > 0 {
                        withAnimation(DesignTokens.Animation.standard) { appState.selectedTab = tabs[i - 1] }
                    }
                }
        )
        // Keep the backend's stored timezone in sync with the device — drives greetings, "today"
        // boundaries, working-hours windows, and scheduling.
        .task { await syncDeviceTimezone() }
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

    private func syncDeviceTimezone() async {
        struct Body: Encodable { let timezone: String }
        struct Resp: Decodable { let timezone: String? }
        let _: Resp? = try? await APIClient.shared.patch(
            "/api/v1/users/me/profile", body: Body(timezone: TimeZone.current.identifier)
        )
    }
}
