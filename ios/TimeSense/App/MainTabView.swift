import SwiftUI

/// The root tab shell. Unlike a stock `TabView` (which swaps content with no animation), this lays
/// the five screens out side-by-side in a pager and slides between them — so both tapping a tab and
/// swiping horizontally produce a visible slide. All screens stay mounted, so each tab keeps its own
/// scroll position and navigation state when you move away and back.
struct MainTabView: View {
    @EnvironmentObject private var appState: AppState
    @ObservedObject private var router = DeepLinkRouter.shared

    private let tabs = AppState.Tab.allCases

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            HStack(spacing: 0) {
                ForEach(tabs, id: \.self) { tab in
                    screen(for: tab)
                        .frame(width: w, height: geo.size.height)
                }
            }
            .frame(width: w, height: geo.size.height, alignment: .leading)
            .offset(x: -CGFloat(appState.selectedTab.rawValue) * w)
            .animation(DesignTokens.Animation.standard, value: appState.selectedTab)
            .clipped()
            .contentShape(Rectangle())
            // Swipe horizontally to move between tabs (in addition to tapping the bar). Low-priority +
            // predominantly-horizontal + distance-thresholded, evaluated only .onEnded, so it doesn't
            // fight vertical scrolling or Today's row swipe-to-reveal (a child gesture wins over this).
            .gesture(
                DragGesture(minimumDistance: 30, coordinateSpace: .local)
                    .onEnded { value in
                        let dx = value.translation.width, dy = value.translation.height
                        guard abs(dx) > 80, abs(dx) > abs(dy) * 1.6 else { return }
                        let i = appState.selectedTab.rawValue
                        if dx < 0, i < tabs.count - 1 {
                            appState.selectedTab = tabs[i + 1]
                        } else if dx > 0, i > 0 {
                            appState.selectedTab = tabs[i - 1]
                        }
                    }
            )
        }
        .ignoresSafeArea(.keyboard)
        .safeAreaInset(edge: .bottom, spacing: 0) {
            TabBar(selected: $appState.selectedTab)
        }
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

    @ViewBuilder
    private func screen(for tab: AppState.Tab) -> some View {
        switch tab {
        case .now: NowView()
        case .today: TodayView()
        case .capture: CaptureView()
        case .insights: InsightsView()
        case .settings: SettingsView()
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

// MARK: - Bottom bar

/// Custom bottom tab bar (a stock `TabView` bar can't sit over a sliding pager). Mirrors the native
/// look — icon + label, accent when selected — over a blurred material with a hairline top edge.
private struct TabBar: View {
    @Binding var selected: AppState.Tab

    private struct Item { let tab: AppState.Tab; let title: String; let icon: String }
    private let items: [Item] = [
        .init(tab: .now, title: "Now", icon: "target"),
        .init(tab: .today, title: "Today", icon: "calendar"),
        .init(tab: .capture, title: "Capture", icon: "plus.circle.fill"),
        .init(tab: .insights, title: "Insights", icon: "chart.bar.fill"),
        .init(tab: .settings, title: "Settings", icon: "gearshape.fill"),
    ]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(items, id: \.tab) { item in
                let isSelected = selected == item.tab
                Button {
                    selected = item.tab
                } label: {
                    VStack(spacing: 3) {
                        Image(systemName: item.icon)
                            .font(.system(size: 20, weight: .regular))
                        Text(item.title)
                            .font(.system(size: 10, weight: .medium))
                    }
                    .foregroundColor(isSelected ? DesignTokens.Color.accent : DesignTokens.Color.textSecondary)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 8)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(item.title)
                .accessibilityAddTraits(isSelected ? [.isSelected] : [])
            }
        }
        .padding(.bottom, 2)
        .background(.bar)
        .overlay(alignment: .top) {
            Divider().opacity(0.5)
        }
    }
}
