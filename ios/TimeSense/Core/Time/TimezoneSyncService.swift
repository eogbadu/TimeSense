import Foundation

/// Keeps the backend's stored profile timezone matching the device, wherever in the world the
/// device is.
///
/// The backend derives "today", greetings, working-hours windows, auto-scheduling slots and
/// check-in notification times from `user_profiles.timezone`. If that value goes stale the whole
/// app is wrong by the offset between the two zones.
///
/// This previously lived as a `.task { }` on `MainTabView`, which fires once when the view is first
/// created and never again — `MainTabView` stays mounted for the life of the process. A user who
/// flew anywhere and resumed the app from the background (the normal case; iOS rarely kills a
/// recently used app) kept their old timezone indefinitely. The single attempt also swallowed every
/// error with `try?`, and it happened at launch — exactly when the network is least reliable, right
/// after landing.
///
/// So this syncs on three triggers, none of them region-specific:
///   1. app launch,
///   2. every return to the foreground (`scenePhase` → `.active`),
///   3. `NSSystemTimeZoneDidChange` — the same system notification that updates the iPhone's own
///      clock when a plane lands.
///
/// It PATCHes only when the identifier actually changed, and retries with backoff on failure so a
/// bad network moment doesn't strand the user in the wrong zone until their next cold start.
@MainActor
final class TimezoneSyncService: ObservableObject {
    static let shared = TimezoneSyncService()

    /// The identifier the backend most recently accepted. Nil until the first successful sync, so
    /// the first attempt always sends.
    private(set) var lastSyncedIdentifier: String?

    private var inFlight: Task<Void, Never>?
    private var observer: NSObjectProtocol?

    private let maxAttempts = 4
    private let baseBackoff: UInt64 = 2_000_000_000   // 2s, doubling

    private init() {}

    /// Begin observing system timezone changes. Safe to call more than once.
    func start() {
        guard observer == nil else { return }
        observer = NotificationCenter.default.addObserver(
            forName: .NSSystemTimeZoneDidChange, object: nil, queue: .main
        ) { [weak self] _ in
            // The device just changed zone — this is the landed-in-a-new-country case.
            Task { @MainActor in self?.sync(reason: "system timezone changed") }
        }
        sync(reason: "launch")
    }

    /// Call when the app returns to the foreground. Cheap: a no-op unless the zone actually moved.
    func syncIfNeeded(reason: String = "foreground") {
        sync(reason: reason)
    }

    private func sync(reason: String) {
        let current = TimeZone.current.identifier
        guard current != lastSyncedIdentifier else { return }
        inFlight?.cancel()
        inFlight = Task { [weak self] in await self?.push(current, reason: reason) }
    }

    private func push(_ identifier: String, reason: String) async {
        struct Body: Encodable { let timezone: String }
        struct Resp: Decodable { let timezone: String? }

        for attempt in 1...maxAttempts {
            if Task.isCancelled { return }
            do {
                let _: Resp = try await APIClient.shared.patch(
                    "/api/v1/users/me/profile", body: Body(timezone: identifier)
                )
                lastSyncedIdentifier = identifier
                print("[Timezone] synced \(identifier) (\(reason))")
                return
            } catch {
                // Don't swallow it — a silently failed sync is what left the stored zone stale.
                print("[Timezone] sync attempt \(attempt)/\(maxAttempts) for \(identifier) failed: \(error)")
                if attempt == maxAttempts { return }
                try? await Task.sleep(nanoseconds: baseBackoff << UInt64(attempt - 1))
            }
        }
    }
}
