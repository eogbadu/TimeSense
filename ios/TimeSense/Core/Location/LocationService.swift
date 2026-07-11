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

    // Geofence events report a crossing but iOS's CLRegionState/`requestState` reflects the last
    // *cached* location, which right after a boundary crossing is stale (still the pre-crossing spot)
    // — that inverted the arrive/leave message. So on a crossing we request a *fresh* fix and derive
    // inside/outside from the real distance to the place center, deduping on a genuine change.
    private var lastRegionState: [String: Bool] = [:]   // regionId -> isInside
    private var pendingEvents: [String: Bool] = [:]      // regionId -> the raw event's direction (true=enter), pending a fresh fix

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
        if !places.isEmpty { syncPlaces() }   // keep the backend's copy in sync on launch
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
        syncPlaces()
    }

    func removePlace(_ place: SavedPlace) {
        manager.stopMonitoring(for: region(for: place))
        places.removeAll { $0.id == place.id }
        persistPlaces()
        syncPlaces()
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
        // Re-arm monitoring after (re)launch and sync the current place. requestState only updates
        // the backend place (it never seeds lastRegionState — see didDetermineState — so it can't
        // dedup a real relaunch event).
        let monitored = manager.monitoredRegions.map(\.identifier)
        for p in places {
            let r = region(for: p)
            if !monitored.contains(p.id) { manager.startMonitoring(for: r) }
            manager.requestState(for: r)
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

    /// Sync saved places (with coordinates) to the backend so the engine can resolve errands and
    /// compute real travel time. These are deliberate, user-named places — not a location trail.
    func syncPlaces() {
        struct PlaceBody: Encodable {
            let name: String; let place_type: String?
            let latitude: Double; let longitude: Double; let is_preferred: Bool
        }
        struct Payload: Encodable { let places: [PlaceBody] }
        let payload = Payload(places: places.map {
            PlaceBody(name: $0.name, place_type: Self.placeType(for: $0.name),
                      latitude: $0.latitude, longitude: $0.longitude, is_preferred: true)
        })
        Task {
            struct Resp: Decodable { let name: String }
            let _: [Resp]? = try? await APIClient.shared.put("/api/v1/places", body: payload)
        }
    }

    private static func placeType(for name: String) -> String? {
        let n = name.lowercased()
        for (kw, type) in [("walmart", "walmart"), ("target", "target"), ("costco", "costco"),
                           ("grocery", "grocery_store"), ("pharmacy", "pharmacy"),
                           ("gym", "gym"), ("school", "school")] where n.contains(kw) {
            return type
        }
        return nil
    }

    /// Tell the backend the user's current place (nil = away) so it can shape the recommendation.
    private func postPlace(placeName: String?, isHome: Bool) async {
        struct Body: Encodable { let place_name: String?; let is_home: Bool }
        struct Resp: Decodable { let place_name: String? }
        let _: Resp? = try? await APIClient.shared.post(
            "/api/v1/location/place", body: Body(place_name: placeName, is_home: isHome)
        )
    }

    /// Resolve a geofence crossing once we know the user's true inside/outside for the place: keep the
    /// backend's current place in sync, dedup against the last known state, and notify on a real change.
    private func resolveCrossing(regionId: String, isInside: Bool) {
        guard let place = places.first(where: { $0.id == regionId }) else { return }
        let previous = lastRegionState[regionId]
        lastRegionState[regionId] = isInside
        if isInside {
            let isHome = place.name.caseInsensitiveCompare("home") == .orderedSame
            Task { await postPlace(placeName: place.name, isHome: isHome) }
        } else if !lastRegionState.values.contains(true) {
            // Left this place and not inside any other tracked place → you're out and about.
            Task { await postPlace(placeName: nil, isHome: false) }
        }
        guard previous != isInside else { return }   // dedup stale/duplicate crossings
        Task { await notifyBestTask(placeName: place.name, entered: isInside) }
    }

    private func notifyBestTask(placeName: String, entered: Bool) async {
        // Ask the full engine for its recommendation here (the app already posted the current place),
        // and use its LLM-phrased notification text. Deterministic fallback is built into the endpoint.
        struct Rec: Decodable {
            let title: String
            let message: String
            let domain: String
        }
        let rec: Rec? = try? await APIClient.shared.get("/api/v1/now/recommendation")
        if let rec, rec.domain != "fallback" {
            // A real, worthwhile recommendation → lead with the LLM text.
            fireNotification(title: rec.title, body: rec.message)
        } else {
            // Nothing pressing → a light acknowledgement rather than a nagging task push.
            let verb = entered ? "You're at" : "You left"
            fireNotification(title: "TimeSense", body: "\(verb) \(placeName).")
        }
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

    // On a crossing, request a *fresh* fix (see pendingEvents note) and resolve inside/outside from the
    // real distance in didUpdateLocations — we no longer derive direction from the stale CLRegionState.
    func locationManager(_ manager: CLLocationManager, didEnterRegion region: CLRegion) {
        pendingEvents[region.identifier] = true
        manager.requestLocation()
    }

    func locationManager(_ manager: CLLocationManager, didExitRegion region: CLRegion) {
        pendingEvents[region.identifier] = false
        manager.requestLocation()
    }

    // Only the stationary seed/sync path (registerGeofence / reregisterGeofences call requestState)
    // reaches here now. Its job is solely to keep the backend's current place in sync at launch — it
    // never notifies and never seeds lastRegionState, so a real background-relaunch crossing still
    // fires exactly once via didUpdateLocations.
    func locationManager(_ manager: CLLocationManager, didDetermineState state: CLRegionState, for region: CLRegion) {
        guard state == .inside, let place = places.first(where: { $0.id == region.identifier }) else { return }
        let isHome = place.name.caseInsensitiveCompare("home") == .orderedSame
        Task { await postPlace(placeName: place.name, isHome: isHome) }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        objectWillChange.send()
        guard !pendingEvents.isEmpty, let fix = locations.last else { return }
        // Only trust a genuinely fresh fix — a stale cached one is exactly what inverted the messages.
        guard abs(fix.timestamp.timeIntervalSinceNow) <= 60 else { return }
        let events = pendingEvents
        pendingEvents.removeAll()
        for (regionId, _) in events {
            guard let place = places.first(where: { $0.id == regionId }) else { continue }
            let center = CLLocation(latitude: place.latitude, longitude: place.longitude)
            resolveCrossing(regionId: regionId, isInside: fix.distance(from: center) <= place.radius)
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // Couldn't get a fresh fix for the crossing → fall back to the raw event's direction so the
        // user still gets a (correct-in-the-common-case) arrive/leave notification.
        guard !pendingEvents.isEmpty else { return }
        let events = pendingEvents
        pendingEvents.removeAll()
        for (regionId, enteredEvent) in events {
            resolveCrossing(regionId: regionId, isInside: enteredEvent)
        }
    }
}
