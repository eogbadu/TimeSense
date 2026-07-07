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

    func savePlace(named name: String) {
        guard let loc = manager.location else { return }
        var updated = places.filter { $0.name.caseInsensitiveCompare(name) != .orderedSame }
        let place = SavedPlace(
            id: UUID().uuidString, name: name,
            latitude: loc.coordinate.latitude, longitude: loc.coordinate.longitude, radius: 130
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
        manager.startMonitoring(for: region(for: place))
    }

    private func reregisterGeofences() {
        let monitored = manager.monitoredRegions.map(\.identifier)
        for p in places where !monitored.contains(p.id) { registerGeofence(p) }
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

    func locationManager(_ manager: CLLocationManager, didEnterRegion region: CLRegion) {
        handleRegionEvent(region.identifier, entered: true)
    }

    func locationManager(_ manager: CLLocationManager, didExitRegion region: CLRegion) {
        handleRegionEvent(region.identifier, entered: false)
    }

    // manager.location is updated automatically; these satisfy requestLocation().
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        objectWillChange.send()
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {}
}
