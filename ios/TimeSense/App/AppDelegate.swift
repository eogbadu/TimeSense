import UIKit
#if canImport(FirebaseCore)
import FirebaseCore
#endif

/// Handles process launch — including background relaunch from a geofence event — so Firebase is
/// configured and LocationService is alive to receive region enter/exit callbacks. Also registers
/// for APNs remote push and syncs the device token to the backend.
final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        #if canImport(FirebaseCore)
        FirebaseApp.configure()
        #endif
        LocationService.shared.start()
        // Request notification permission (idempotent) then register for remote push. The token
        // arrives in didRegisterForRemoteNotificationsWithDeviceToken.
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            guard granted else { return }
            DispatchQueue.main.async { application.registerForRemoteNotifications() }
        }
        return true
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task {
            struct Body: Encodable { let token: String; let platform: String }
            struct Ack: Decodable { let ok: Bool }
            let _: Ack? = try? await APIClient.shared.put(
                "/api/v1/devices", body: Body(token: token, platform: "ios")
            )
        }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        // Non-fatal — the app still works without remote push (local notifications continue).
        print("Remote notification registration failed: \(error.localizedDescription)")
    }
}
