import CoreLocation
import Foundation
import UIKit
import UserNotifications

/// A place the user chose to save (Home/Work). We persist only these user-chosen centers — never a
/// raw location track (per the product rule "raw location points are never persisted").
struct SavedPlace: Codable, Identifiable, Equatable {
    let id: String
    var name: String
    var latitude: Double
    var longitude: Double
    var radius: Double   // geofence radius in meters
}

/// Owns CoreLocation. With "Always" permission it monitors geofences around the user's saved places;
/// on enter/exit iOS wakes the app (even if terminated), and we recompute the best next task and fire
/// a local notification. "When In Use" gives a location-aware Now only while the app is open.
final class LocationService: NSObject, ObservableObject {
    static let shared = LocationService()

    private let manager = CLLocationManager()
    private let placesKey = "saved_places"

    // Geofence events are laggy and can arrive stale/out-of-order, so we don't trust them directly:
    // on any event we ask iOS for the authoritative current state and only notify on a real change.
    private var lastRegionState: [String: Bool] = [:]   // regionId -> isInside
    private var pendingEvents: Set<String> = []          // regions whose state query came from an event

    @Published private(set) var authorizationStatus: CLAuthorizationStatus = .notDetermined
    @Published private(set) var places: [SavedPlace] = []

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        authorizationStatus = manager.authorizationStatus
        loadPlaces()
    }

    /// Called at launch (incl. background relaunch from a geofence event) so we re-register regions.
    func start() {
        authorizationStatus = manager.authorizationStatus
        if authorizationStatus == .authorizedAlways {
            manager.allowsBackgroundLocationUpdates = true
            reregisterGeofences()
        }
    }

    var currentLocation: CLLocation? { manager.location }

    /// Step up permission: not-determined → When-In-Use → (on next tap) Always. Also asks for
    /// notification permission so we can alert on arrival.
    func requestPermission() {
        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse:
            manager.requestAlwaysAuthorization()
        default:
            break
        }
        requestNotificationPermission()
    }

    func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
    }

    var isAuthorized: Bool {
        authorizationStatus == .authorizedWhenInUse || authorizationStatus == .authorizedAlways
    }

    /// Grab a single fresh fix so "Save current place" has coordinates to use.
    func requestOneTimeLocation() {
        if isAuthorized { manager.requestLocation() }
    }

    /// Deep-link to this app's iOS Settings page — the reliable way to enable "Always" (iOS often
    /// won't show the in-app upgrade prompt).
    func openAppSettings() {
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        DispatchQueue.main.async { UIApplication.shared.open(url) }
    }

    // MARK: - Saved places

    func savePlace(named rawName: String) {
        let name = rawName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty, let loc = manager.location else { return }
        let isNew = !places.contains { $0.name.caseInsensitiveCompare(name) == .orderedSame }
        // iOS monitors at most 20 regions; don't exceed it.
        guard !isNew || places.count < 20 else { return }
        var updated = places.filter { $0.name.caseInsensitiveCompare(name) != .orderedSame }
        let place = SavedPlace(
            id: UUID().uuidString, name: name,
            latitude: loc.coordinate.latitude, longitude: loc.coordinate.longitude, radius: 100
        )
        updated.append(place)
        places = updated
        persistPlaces()
        registerGeofence(place)
    }

    func removePlace(_ place: SavedPlace) {
        manager.stopMonitoring(for: region(for: place))
        places.removeAll { $0.id == place.id }
        persistPlaces()
    }

    // MARK: - Geofencing

    private func region(for place: SavedPlace) -> CLCircularRegion {
        let r = CLCircularRegion(
            center: CLLocationCoordinate2D(latitude: place.latitude, longitude: place.longitude),
            radius: place.radius, identifier: place.id
        )
        r.notifyOnEntry = true
        r.notifyOnExit = true
        return r
    }

    private func registerGeofence(_ place: SavedPlace) {
        guard CLLocationManager.isMonitoringAvailable(for: CLCircularRegion.self) else { return }
        let r = region(for: place)
        manager.startMonitoring(for: r)
        manager.requestState(for: r)   // seed current state (no notification for the seed)
    }

    private func reregisterGeofences() {
        // Re-arm monitoring after (re)launch. We do NOT seed state here — on a background relaunch
        // from a geofence event, seeding could dedup the very event that woke us. With no seed, the
        // triggering event (previous == nil) correctly fires once.
        let monitored = manager.monitoredRegions.map(\.identifier)
        for p in places where !monitored.contains(p.id) {
            manager.startMonitoring(for: region(for: p))
        }
    }

    // MARK: - Persistence (only user-chosen place centers)

    private func loadPlaces() {
        if let data = UserDefaults.standard.data(forKey: placesKey),
           let decoded = try? JSONDecoder().decode([SavedPlace].self, from: data) {
            places = decoded
        }
    }

    private func persistPlaces() {
        if let data = try? JSONEncoder().encode(places) {
            UserDefaults.standard.set(data, forKey: placesKey)
        }
    }

    // MARK: - On arrival → recompute → notify

    private func handleRegionEvent(_ identifier: String, entered: Bool) {
        let placeName = places.first { $0.id == identifier }?.name ?? "a saved place"
        Task { await notifyBestTask(placeName: placeName, entered: entered) }
    }

    private func notifyBestTask(placeName: String, entered: Bool) async {
        struct Ctx: Decodable {
            let best_task: BestTask?
            struct BestTask: Decodable { let title: String }
        }
        let verb = entered ? "You're at" : "You left"
        let ctx: Ctx? = try? await APIClient.shared.get("/api/v1/now")
        let body: String
        if let title = ctx?.best_task?.title {
            body = "\(verb) \(placeName). Best next: \(title)."
        } else {
            body = "\(verb) \(placeName). Open TimeSense for your best next task."
        }
        fireNotification(title: "TimeSense", body: body)
    }

    private func fireNotification(title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request)
    }
}

extension LocationService: CLLocationManagerDelegate {
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorizationStatus = manager.authorizationStatus
        start()
    }

    // On any enter/exit, verify the *actual* current state with iOS rather than trusting the (often
    // stale/late) event, then notify only on a genuine change.
    func locationManager(_ manager: CLLocationManager, didEnterRegion region: CLRegion) {
        pendingEvents.insert(region.identifier)
        manager.requestState(for: region)
    }

    func locationManager(_ manager: CLLocationManager, didExitRegion region: CLRegion) {
        pendingEvents.insert(region.identifier)
        manager.requestState(for: region)
    }

    func locationManager(_ manager: CLLocationManager, didDetermineState state: CLRegionState, for region: CLRegion) {
        let cameFromEvent = pendingEvents.remove(region.identifier) != nil
        guard state != .unknown else { return }
        let isInside = (state == .inside)
        let previous = lastRegionState[region.identifier]
        lastRegionState[region.identifier] = isInside
        // Notify only for a real event that reflects an actual change (dedups stale/out-of-order
        // events, e.g. a late "exit" that arrives while you're actually back inside).
        if cameFromEvent, previous != isInside {
            handleRegionEvent(region.identifier, entered: isInside)
        }
    }

    // manager.location is updated automatically; these satisfy requestLocation().
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        objectWillChange.send()
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {}
}
