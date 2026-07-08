import UIKit
#if canImport(FirebaseCore)
import FirebaseCore
#endif

/// Debug-only logging — compiles to nothing in release builds (the `@autoclosure` isn't even
/// evaluated), so these diagnostics stay handy locally without shipping to production.
@inline(__always)
func debugLog(_ message: @autoclosure () -> String) {
    #if DEBUG
    print(message())
    #endif
}

/// Handles process launch — including background relaunch from a geofence event — so Firebase is
/// configured and LocationService is alive to receive region enter/exit callbacks. Also registers
/// for APNs remote push and syncs the device token to the backend.
final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Loud launch marker — if you DON'T see this in the console, you're running a stale binary
        // (clean build + run from Xcode). Bump the tag when verifying a fresh build is installed.
        debugLog("🚀🚀🚀 TimeSense launched — push-registration build TIME-127 🚀🚀🚀")
        #if canImport(FirebaseCore)
        FirebaseApp.configure()
        #endif
        LocationService.shared.start()
        // Register for remote push UNCONDITIONALLY to obtain the APNs token — the token is separate
        // from alert permission, so we shouldn't gate it on the permission prompt. We request alert
        // permission separately (for showing the banners).
        debugLog("📡 Calling registerForRemoteNotifications()…")
        application.registerForRemoteNotifications()
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
            debugLog("🔔 Notification permission granted=\(granted) error=\(String(describing: error))")
        }
        return true
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        debugLog("✅ APNs device token: \(token)")   // visible in the Xcode console for debugging
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
        // Almost always means the "Push Notifications" capability isn't on the provisioning profile.
        debugLog("❌ Remote notification registration FAILED: \(error.localizedDescription)")
    }
}

extension AppDelegate: UNUserNotificationCenterDelegate {
    /// Show notifications (banner + sound) even when the app is in the foreground — otherwise iOS
    /// silently suppresses them, which looks like "the push never arrived" while testing.
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        debugLog("🔔 Notification presented in foreground: \(notification.request.content.title)")
        completionHandler([.banner, .sound, .badge])
    }
}
