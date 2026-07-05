import WidgetKit

/// Shared timeline entry/provider for all three widgets. Reads the snapshot the host app wrote
/// to the App Group container — no network calls happen here.
struct SnapshotEntry: TimelineEntry {
    let date: Date
    let snapshot: WidgetSnapshot
}

struct SnapshotProvider: TimelineProvider {
    func placeholder(in context: Context) -> SnapshotEntry {
        SnapshotEntry(date: Date(), snapshot: .empty)
    }

    func getSnapshot(in context: Context, completion: @escaping (SnapshotEntry) -> Void) {
        completion(SnapshotEntry(date: Date(), snapshot: WidgetSnapshot.load() ?? .empty))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SnapshotEntry>) -> Void) {
        let snapshot = WidgetSnapshot.load() ?? .empty
        let entry = SnapshotEntry(date: Date(), snapshot: snapshot)

        // Refresh at the next event's start if that's sooner than the default 30-minute cadence,
        // so the widget doesn't show a stale "next event" after it's already begun.
        let defaultRefresh = Date().addingTimeInterval(30 * 60)
        let nextRefresh = min(defaultRefresh, snapshot.nextEvent?.start ?? defaultRefresh)

        completion(Timeline(entries: [entry], policy: .after(nextRefresh)))
    }
}
