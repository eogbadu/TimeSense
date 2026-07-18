import AppIntents

/// Exposes the App Intents to Siri and the Shortcuts app with natural phrases. Every phrase must
/// include \(.applicationName) so Siri can disambiguate to TimeSense.
struct TimeSenseShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: WhatToDoNextIntent(),
            phrases: [
                "What should I do next in \(.applicationName)",
                "Ask \(.applicationName) what to do next",
            ],
            shortTitle: "What to do next",
            systemImageName: "calendar.badge.clock"
        )
        AppShortcut(
            intent: LogLunchIntent(),
            phrases: [
                "Log lunch in \(.applicationName)",
                "Tell \(.applicationName) I ate lunch",
            ],
            shortTitle: "Log lunch",
            systemImageName: "fork.knife"
        )
        AppShortcut(
            intent: StartFocusIntent(),
            phrases: [
                "Start focus in \(.applicationName)",
                "Start a \(.applicationName) focus session",
            ],
            shortTitle: "Start focus",
            systemImageName: "scope"
        )
        AppShortcut(
            intent: MarkDoneIntent(),
            phrases: [
                "Mark done in \(.applicationName)",
                "Tell \(.applicationName) I finished this",
            ],
            shortTitle: "Mark done",
            systemImageName: "checkmark.circle"
        )
        AppShortcut(
            intent: ReplanDayIntent(),
            phrases: [
                "Replan my day in \(.applicationName)",
                "Ask \(.applicationName) to replan my day",
            ],
            shortTitle: "Replan day",
            systemImageName: "arrow.triangle.2.circlepath"
        )
    }
}
