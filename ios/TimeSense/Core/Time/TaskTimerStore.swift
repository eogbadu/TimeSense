import Foundation

/// A running "how long is this actually taking?" timer, persisted outside view state.
///
/// The first version (TIME-287) kept this in a dictionary on the view model and mirrored it in
/// `@State` on the button row. Both were wrong:
///
///   * SwiftUI recreates the row when the recommendation changes or the tab is revisited, which
///     reset the `@State` and made a running timer disappear — the user had to Agree and Start
///     again, losing the elapsed time;
///   * the dictionary lived only in memory, so force-quitting the app lost the timer entirely.
///
/// A timer that silently forgets is worse than no timer at all, because the user believes their
/// work is being measured when it isn't — and the measurement is the whole point, since it feeds
/// the per-type duration learning (TIME-286).
///
/// So the source of truth is a persisted START TIMESTAMP. Elapsed time is always derived from it
/// rather than accumulated by a ticking counter, which means backgrounding, suspension or the
/// device sleeping cannot cause drift or under-counting.
struct RunningTaskTimer: Codable, Equatable {
    let taskId: String
    let taskTitle: String
    let startedAt: Date
    /// The estimate shown when the timer started — used by the overrun prompt (TIME-299) and to
    /// pre-fill the duration sheet.
    let estimatedMinutes: Int?

    var elapsed: TimeInterval { Date().timeIntervalSince(startedAt) }

    /// Whole minutes, for submission. Sub-minute time is a display concern only.
    var elapsedMinutes: Int { Int((elapsed / 60).rounded()) }
}

@MainActor
final class TaskTimerStore: ObservableObject {
    static let shared = TaskTimerStore()

    /// Nil when nothing is being timed. Only one task is timed at a time — the user is doing one
    /// thing, and "which of my three timers is this?" is exactly the kind of management the product
    /// is supposed to remove.
    @Published private(set) var running: RunningTaskTimer?

    private let key = "runningTaskTimer"
    private let defaults: UserDefaults

    private init() {
        // Reuse the App Group suite the widgets already use, so a timer could later be surfaced on
        // the home screen without moving storage.
        self.defaults = UserDefaults(suiteName: WidgetSnapshot.appGroupID) ?? .standard
        self.running = Self.load(from: defaults, key: key)
    }

    func start(taskId: String, title: String, estimatedMinutes: Int?) {
        let timer = RunningTaskTimer(taskId: taskId, taskTitle: title,
                                     startedAt: Date(), estimatedMinutes: estimatedMinutes)
        running = timer
        persist(timer)
    }

    func stop() {
        running = nil
        defaults.removeObject(forKey: key)
    }

    /// Clear the timer only if it belongs to `taskId` — so completing some OTHER task can't silently
    /// discard a timer the user still has running.
    func stopIfTiming(taskId: String) {
        guard running?.taskId == taskId else { return }
        stop()
    }

    func isTiming(taskId: String) -> Bool { running?.taskId == taskId }

    /// Elapsed seconds for the given task, or nil when it isn't the one being timed.
    func elapsed(taskId: String) -> TimeInterval? {
        guard let running, running.taskId == taskId else { return nil }
        return running.elapsed
    }

    private func persist(_ timer: RunningTaskTimer) {
        guard let data = try? JSONEncoder().encode(timer) else { return }
        defaults.set(data, forKey: key)
    }

    private static func load(from defaults: UserDefaults, key: String) -> RunningTaskTimer? {
        guard let data = defaults.data(forKey: key),
              let timer = try? JSONDecoder().decode(RunningTaskTimer.self, from: data)
        else { return nil }
        // Drop a timer left running absurdly long (e.g. started and forgotten overnight). It can't
        // produce a usable observation, and restoring it would show the user a nonsense number.
        guard timer.elapsed < Self.maxRestorableAge else { return nil }
        return timer
    }

    /// Beyond this, a restored timer is assumed to be abandoned rather than genuinely running.
    /// `nonisolated` because it is a plain constant — inheriting the class's @MainActor isolation
    /// makes it unusable from a non-isolated context, which is a hard error under Swift 6.
    nonisolated static let maxRestorableAge: TimeInterval = 12 * 60 * 60
}

/// Formats elapsed time so it is obviously MOVING. The first version showed whole minutes only and
/// ticked every 30s, so for the first minute it read "Timing…" and never visibly changed — the user
/// had no evidence the timer was alive (TIME-298).
func formatElapsed(_ interval: TimeInterval) -> String {
    let total = max(0, Int(interval))
    let h = total / 3600, m = (total % 3600) / 60, s = total % 60
    return h > 0
        ? String(format: "%d:%02d:%02d", h, m, s)
        : String(format: "%d:%02d", m, s)
}
