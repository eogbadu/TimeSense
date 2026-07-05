import Foundation

/// Request body for POST /api/v1/sleep/events — matches the backend SleepWakeEventIn (TIME-042).
private struct SleepWakeSyncRequest: Encodable {
    let wakeTime: Date
    let sleepStart: Date?
    let source: String

    enum CodingKeys: String, CodingKey {
        case wakeTime = "wake_time"
        case sleepStart = "sleep_start"
        case source
    }
}

private struct SleepWakeSyncResponse: Decodable {
    let id: String
    let replanSuggested: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case replanSuggested = "replan_suggested"
    }
}

enum HealthConnectState: Equatable {
    case idle
    case requesting
    case syncing
    case synced(replanSuggested: Bool)
    case noData
    case unavailable
    case error(String)
}

#if canImport(HealthKit)
import HealthKit

/// Reads Apple Health sleep-analysis samples and syncs the most recent wake time to the backend.
/// Read-only — TimeSense never writes to HealthKit. The backend gates on health_data consent and
/// proposes a morning replan on a late wake (TIME-042).
@MainActor
final class HealthService: ObservableObject {
    @Published private(set) var state: HealthConnectState = .idle

    private let store = HKHealthStore()

    private var sleepType: HKCategoryType? {
        HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)
    }

    /// Requests read authorization for sleep analysis, then reads + syncs the latest wake.
    func connectAndSync() async {
        guard HKHealthStore.isHealthDataAvailable(), let sleepType else {
            state = .unavailable
            return
        }
        state = .requesting
        do {
            try await store.requestAuthorization(toShare: [], read: [sleepType])
        } catch {
            state = .error("Couldn't access Apple Health.")
            return
        }
        await syncLatestSleep()
    }

    /// Reads the most recent sleep window and POSTs its wake time to the backend.
    func syncLatestSleep() async {
        guard let window = await readMostRecentSleepWindow() else {
            state = .noData
            return
        }
        state = .syncing
        do {
            let response: SleepWakeSyncResponse = try await APIClient.shared.post(
                "/api/v1/sleep/events",
                body: SleepWakeSyncRequest(
                    wakeTime: window.wake,
                    sleepStart: window.sleepStart,
                    source: "healthkit"
                )
            )
            state = .synced(replanSuggested: response.replanSuggested)
        } catch let error as APIError {
            state = .error(error.errorDescription ?? "Sync failed.")
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    /// The most recent night's sleep: earliest "asleep" start and latest "asleep" end (= wake).
    private func readMostRecentSleepWindow() async -> (sleepStart: Date, wake: Date)? {
        guard let sleepType else { return nil }
        let asleep = HKCategoryValueSleepAnalysis.allAsleepValues.map(\.rawValue)

        let sort = [NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)]
        let samples: [HKCategorySample] = await withCheckedContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: sleepType,
                predicate: nil,
                limit: 200,
                sortDescriptors: sort
            ) { _, results, _ in
                continuation.resume(returning: (results as? [HKCategorySample]) ?? [])
            }
            store.execute(query)
        }

        let asleepSamples = samples.filter { asleep.contains($0.value) }
        guard let latest = asleepSamples.first else { return nil }

        // Group the contiguous most-recent sleep session: samples whose end is within ~6h of the
        // latest wake belong to the same night.
        let sameNight = asleepSamples.filter {
            latest.endDate.timeIntervalSince($0.endDate) < 6 * 60 * 60
        }
        let sleepStart = sameNight.map(\.startDate).min() ?? latest.startDate
        return (sleepStart, latest.endDate)
    }
}

#else

/// Stub used when HealthKit isn't linkable (mirrors the AuthService Firebase-stub pattern).
@MainActor
final class HealthService: ObservableObject {
    @Published private(set) var state: HealthConnectState = .unavailable
    func connectAndSync() async { state = .unavailable }
    func syncLatestSleep() async { state = .unavailable }
}

#endif
