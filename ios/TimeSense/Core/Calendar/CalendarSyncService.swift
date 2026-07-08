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
    /// The fetched events (sync window), for on-screen display (e.g. the Today timeline).
    @Published private(set) var events: [CalEvent] = []

    struct CalEvent: Identifiable, Equatable {
        let id: String
        let title: String
        let start: Date
        let end: Date
        let location: String?
        let allDay: Bool
    }

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

    // MARK: - Write-back (create events, with the user approving in the native editor)

    /// The store the native event editor writes to.
    var eventStore: EKEventStore { store }

    /// Ensure we can write to the calendar, requesting access if needed. Returns whether granted.
    func ensureWriteAccess() async -> Bool {
        if isAuthorized { return true }
        do {
            let granted: Bool
            if #available(iOS 17.0, *) {
                granted = try await store.requestFullAccessToEvents()
            } else {
                granted = try await store.requestAccess(to: .event)
            }
            if granted { status = .connected }
            return granted
        } catch {
            return false
        }
    }

    /// A draft event (unsaved) the native editor will present for the user to review + confirm.
    func makeDraftEvent(title: String, start: Date, end: Date) -> EKEvent {
        let event = EKEvent(eventStore: store)
        event.title = title
        event.startDate = start
        event.endDate = end
        event.calendar = store.defaultCalendarForNewEvents
        return event
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
        let ekEvents = store.events(matching: predicate).compactMap { ev -> (EKEvent, String, String)? in
            guard let id = ev.eventIdentifier, let title = ev.title, !title.isEmpty,
                  ev.startDate != nil, ev.endDate != nil else { return nil }
            return (ev, id, title)
        }
        // For display (Today timeline).
        events = ekEvents.map { ev, id, title in
            CalEvent(id: id, title: title, start: ev.startDate, end: ev.endDate,
                     location: ev.location, allDay: ev.isAllDay)
        }
        // For the backend/engine.
        let payload: [SyncEvent] = ekEvents.map { ev, id, title in
            SyncEvent(external_id: id, title: title,
                      starts_at: iso.string(from: ev.startDate), ends_at: iso.string(from: ev.endDate),
                      location: ev.location, all_day: ev.isAllDay)
        }
        let resp: SyncResponse? = try? await APIClient.shared.put(
            "/api/v1/calendar/synced", body: SyncPayload(source: "apple", events: payload)
        )
        lastSyncedCount = resp?.synced ?? payload.count
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
