import UIKit
#if canImport(FirebaseCore)
import FirebaseCore
#endif

/// Handles process launch — including background relaunch from a geofence event — so Firebase is
/// configured and LocationService is alive to receive region enter/exit callbacks.
final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        #if canImport(FirebaseCore)
        FirebaseApp.configure()
        #endif
        LocationService.shared.start()
        return true
    }
}
