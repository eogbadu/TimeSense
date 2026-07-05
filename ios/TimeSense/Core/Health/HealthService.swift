// ⚠️ UNVERIFIED — written in a Linux devcontainer with no Xcode/macOS access, so this file has
// never been compiled or run. Before merging feature/TIME-042-sleep-wake-signal into main:
//   1. Open ios/TimeSense.xcodeproj in Xcode on a real Mac.
//   2. Add the "HealthKit" capability under Signing & Capabilities (this generates the
//      entitlements file — do not hand-write one).
//   3. Add an NSHealthShareUsageDescription string via the target's Info tab (or
//      INFOPLIST_KEY_NSHealthShareUsageDescription build setting), e.g.:
//      "Sleep and wake data helps TimeSense adjust your morning plan and understand your energy."
//   4. xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense
//        -destination "platform=iOS Simulator,name=iPhone 15"
//   5. xcodebuild test -project ios/TimeSense.xcodeproj -scheme TimeSense
//        -destination "platform=iOS Simulator,name=iPhone 15"
// Only merge once all of the above pass. See docs/project_memory/known_issues.md.

import Foundation
import HealthKit

/// Reads sleep-analysis samples from HealthKit (read-only) and reports the latest wake time
/// to the backend so MorningReplanService can suggest an adjustment on a late wake-up.
@MainActor
final class HealthService: ObservableObject {
    @Published private(set) var isAuthorized: Bool = false
    @Published private(set) var lastSyncError: String?

    private let store = HKHealthStore()
    private let api = APIClient.shared

    private var sleepType: HKCategoryType? {
        HKObjectType.categoryType(forIdentifier: .sleepAnalysis)
    }

    var isHealthDataAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    /// Requests read-only access to sleep analysis. TimeSense never writes to HealthKit.
    func requestAuthorization() async {
        guard isHealthDataAvailable, let sleepType else {
            lastSyncError = "Health data is not available on this device."
            return
        }
        do {
            try await store.requestAuthorization(toShare: [], read: [sleepType])
            isAuthorized = true
        } catch {
            isAuthorized = false
            lastSyncError = error.localizedDescription
        }
    }

    /// Fetches the most recent sleep-analysis sample and posts it to the backend.
    /// Safe to call repeatedly (e.g. on app foreground) — the backend only proposes
    /// a replan when the wake time is meaningfully later than usual.
    func syncLatestWake() async {
        guard let sample = await fetchLatestSleepSample() else { return }
        do {
            let _: SleepWakeEventResponse = try await api.post(
                "/api/v1/sleep-wake",
                body: SleepWakeLogRequest(
                    wakeTime: sample.endDate,
                    sleepStart: sample.startDate,
                    source: "healthkit"
                )
            )
        } catch let error as APIError {
            lastSyncError = error.localizedDescription ?? "Sleep sync failed."
        } catch {
            lastSyncError = error.localizedDescription
        }
    }

    private func fetchLatestSleepSample() async -> HKCategorySample? {
        guard let sleepType else { return nil }
        return await withCheckedContinuation { continuation in
            let sort = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)
            let query = HKSampleQuery(
                sampleType: sleepType,
                predicate: nil,
                limit: 1,
                sortDescriptors: [sort]
            ) { _, samples, _ in
                continuation.resume(returning: samples?.first as? HKCategorySample)
            }
            store.execute(query)
        }
    }
}

private struct SleepWakeLogRequest: Encodable {
    let wakeTime: Date
    let sleepStart: Date?
    let source: String

    enum CodingKeys: String, CodingKey {
        case wakeTime = "wake_time"
        case sleepStart = "sleep_start"
        case source
    }
}

private struct SleepWakeEventResponse: Decodable {
    let id: String
    let wakeTime: Date
    let sleepStart: Date?
    let source: String

    enum CodingKeys: String, CodingKey {
        case id, source
        case wakeTime = "wake_time"
        case sleepStart = "sleep_start"
    }
}
