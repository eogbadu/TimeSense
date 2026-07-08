import EventKit
import Foundation

/// Reads the device's calendar (EventKit — covers Apple, plus any Google/Exchange calendars the user
/// has added to iOS Calendar) and syncs upcoming events to the backend so the engine can factor the
/// user's schedule. No OAuth — this is a native device permission.
@MainActor
final class CalendarSyncService: ObservableObject {
    static let shared = CalendarSyncService()

    private let store = EKEventStore()
    private let iso = ISO8601DateFormatter()

    enum Status: Equatable { case unknown, notConnected, connecting, connected, denied }

    @Published private(set) var status: Status = .unknown
    @Published private(set) var lastSyncedCount: Int = 0

    init() {
        status = isAuthorized ? .connected : .notConnected
    }

    private var isAuthorized: Bool {
        let s = EKEventStore.authorizationStatus(for: .event)
        if #available(iOS 17.0, *) { return s == .fullAccess }
        return s == .authorized
    }

    /// Request calendar access (read+write) and do a first sync.
    func connect() async {
        status = .connecting
        do {
            let granted: Bool
            if #available(iOS 17.0, *) {
                granted = try await store.requestFullAccessToEvents()
            } else {
                granted = try await store.requestAccess(to: .event)
            }
            guard granted else { status = .denied; return }
            await sync()
            status = .connected
        } catch {
            status = .denied
        }
    }

    /// Re-sync when already authorized (call on launch / when the app foregrounds).
    func syncIfAuthorized() async {
        guard isAuthorized else { return }
        await sync()
        status = .connected
    }

    func disconnect() async {
        // Clear the backend's copy. (Revoking the OS permission itself is done in iOS Settings.)
        let _: SyncResponse? = try? await APIClient.shared.put(
            "/api/v1/calendar/synced", body: SyncPayload(source: "apple", events: [])
        )
        lastSyncedCount = 0
        status = .notConnected
    }

    private func sync() async {
        let start = Date().addingTimeInterval(-12 * 3600)
        let end = Date().addingTimeInterval(36 * 3600)
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: nil)
        let events: [SyncEvent] = store.events(matching: predicate).compactMap { ev in
            guard let id = ev.eventIdentifier, let title = ev.title, !title.isEmpty,
                  let s = ev.startDate, let e = ev.endDate else { return nil }
            return SyncEvent(external_id: id, title: title,
                             starts_at: iso.string(from: s), ends_at: iso.string(from: e),
                             location: ev.location, all_day: ev.isAllDay)
        }
        let resp: SyncResponse? = try? await APIClient.shared.put(
            "/api/v1/calendar/synced", body: SyncPayload(source: "apple", events: events)
        )
        lastSyncedCount = resp?.synced ?? events.count
    }
}

private struct SyncEvent: Encodable {
    let external_id: String
    let title: String
    let starts_at: String
    let ends_at: String
    let location: String?
    let all_day: Bool
}

private struct SyncPayload: Encodable {
    let source: String
    let events: [SyncEvent]
}

private struct SyncResponse: Decodable {
    let synced: Int
}
