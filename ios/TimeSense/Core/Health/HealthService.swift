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

    private var readTypes: Set<HKObjectType> {
        var types: Set<HKObjectType> = [HKObjectType.workoutType()]
        if let sleepType { types.insert(sleepType) }
        for id in [HKQuantityTypeIdentifier.stepCount, .activeEnergyBurned, .appleExerciseTime,
                   .distanceWalkingRunning] {
            if let t = HKQuantityType.quantityType(forIdentifier: id) { types.insert(t) }
        }
        return types
    }

    /// Requests read authorization for sleep + activity + workouts, then reads + syncs everything.
    func connectAndSync() async {
        guard HKHealthStore.isHealthDataAvailable() else {
            state = .unavailable
            return
        }
        state = .requesting
        do {
            try await store.requestAuthorization(toShare: [], read: readTypes)
        } catch {
            state = .error("Couldn't access Apple Health.")
            return
        }
        // Connecting Apple Health is the user granting health-data use — record the consent BEFORE the
        // syncs, since /activity/workouts and /activity/hourly are gated on health_data (TIME-256).
        await grantConsent("health_data")
        await syncActivity()
        await syncLatestSleep()
        await syncWorkouts()
        await syncHourlySteps()
    }

    private func grantConsent(_ type: String) async {
        struct Body: Encodable { let consent_type: String; let granted: Bool }
        struct Ack: Decodable { let granted: Bool }
        _ = try? await APIClient.shared.post("/api/v1/consent/", body: Body(consent_type: type, granted: true)) as Ack
    }

    /// Opportunistic sync used on app launch (only succeeds if authorization was already granted):
    /// daily activity + workouts + hourly steps. Safe to call anytime.
    func syncBackground() async {
        await syncActivity()
        await syncWorkouts()
        await syncHourlySteps()
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

    // MARK: - Activity (steps / active energy / exercise) — best-effort, read-only

    /// Reads today's step/energy/exercise totals and upserts them to the backend. Safe to call
    /// anytime: unauthorized types just return no data and are skipped.
    func syncActivity() async {
        let steps = await sumToday(.stepCount, unit: .count())
        let kcal = await sumToday(.activeEnergyBurned, unit: .kilocalorie())
        let exercise = await sumToday(.appleExerciseTime, unit: .minute())
        guard steps != nil || kcal != nil || exercise != nil else { return }
        // Only infer "sitting" when we actually have step tracking today (avoids false positives).
        let inactive = (steps ?? 0) > 0 ? await inactiveMinutes() : nil

        struct Body: Encodable {
            let steps: Int
            let active_energy_kcal: Int?
            let exercise_minutes: Int?
            let inactive_minutes: Int?
        }
        struct Ack: Decodable { let steps: Int }
        let body = Body(steps: Int(steps ?? 0),
                        active_energy_kcal: kcal.map { Int($0) },
                        exercise_minutes: exercise.map { Int($0) },
                        inactive_minutes: inactive)
        _ = try? await APIClient.shared.post("/api/v1/activity", body: body) as Ack
    }

    /// Minutes since the user last moved meaningfully — inferred from 15-min step buckets over the
    /// last 4h (the most recent bucket with >= 30 steps marks the last active moment).
    private func inactiveMinutes() async -> Int? {
        guard let type = HKQuantityType.quantityType(forIdentifier: .stepCount) else { return nil }
        let now = Date()
        let lookback = now.addingTimeInterval(-4 * 3600)
        let predicate = HKQuery.predicateForSamples(withStart: lookback, end: now, options: .strictStartDate)
        let anchor = Calendar.current.startOfDay(for: now)
        return await withCheckedContinuation { continuation in
            let query = HKStatisticsCollectionQuery(
                quantityType: type, quantitySamplePredicate: predicate,
                options: .cumulativeSum, anchorDate: anchor,
                intervalComponents: DateComponents(minute: 15)
            )
            query.initialResultsHandler = { _, results, _ in
                guard let results else { continuation.resume(returning: nil); return }
                var lastActiveEnd: Date?
                results.enumerateStatistics(from: lookback, to: now) { stat, _ in
                    let steps = stat.sumQuantity()?.doubleValue(for: .count()) ?? 0
                    if steps >= 30 { lastActiveEnd = stat.endDate }
                }
                if let lastActiveEnd {
                    continuation.resume(returning: max(0, Int(now.timeIntervalSince(lastActiveEnd) / 60)))
                } else {
                    // No active bucket in the window → sitting at least the whole window.
                    continuation.resume(returning: Int(now.timeIntervalSince(lookback) / 60))
                }
            }
            store.execute(query)
        }
    }

    private func sumToday(_ id: HKQuantityTypeIdentifier, unit: HKUnit) async -> Double? {
        guard let type = HKQuantityType.quantityType(forIdentifier: id) else { return nil }
        let start = Calendar.current.startOfDay(for: Date())
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date(), options: .strictStartDate)
        return await withCheckedContinuation { continuation in
            let query = HKStatisticsQuery(
                quantityType: type, quantitySamplePredicate: predicate, options: .cumulativeSum
            ) { _, stats, _ in
                continuation.resume(returning: stats?.sumQuantity()?.doubleValue(for: unit))
            }
            store.execute(query)
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

    // MARK: - Workouts (runs / gym) — read-only, powers behavioral patterns

    /// Read recent workouts (last 28d) and upsert them to the backend (deduped by their HealthKit id).
    func syncWorkouts() async {
        let items = await recentWorkouts()
        guard !items.isEmpty else { return }
        struct Body: Encodable { let workouts: [WorkoutSyncItem] }
        struct Ack: Decodable { let accepted: Int }
        _ = try? await APIClient.shared.post("/api/v1/activity/workouts", body: Body(workouts: items)) as Ack
    }

    private func recentWorkouts() async -> [WorkoutSyncItem] {
        let start = Calendar.current.date(byAdding: .day, value: -28, to: Date()) ?? Date()
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date(), options: .strictStartDate)
        let sort = [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)]
        let workouts: [HKWorkout] = await withCheckedContinuation { continuation in
            let query = HKSampleQuery(sampleType: .workoutType(), predicate: predicate,
                                      limit: 200, sortDescriptors: sort) { _, results, _ in
                continuation.resume(returning: (results as? [HKWorkout]) ?? [])
            }
            store.execute(query)
        }
        let distanceType = HKQuantityType.quantityType(forIdentifier: .distanceWalkingRunning)
        let energyType = HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned)
        return workouts.map { w in
            let meters = distanceType.flatMap { w.statistics(for: $0)?.sumQuantity()?.doubleValue(for: .meter()) }
            let kcal = energyType.flatMap { w.statistics(for: $0)?.sumQuantity()?.doubleValue(for: .kilocalorie()) }
            return WorkoutSyncItem(
                external_id: w.uuid.uuidString,
                workout_type: Self.workoutType(w.workoutActivityType),
                started_at: w.startDate, ended_at: w.endDate,
                duration_minutes: Int(w.duration / 60.0),
                distance_meters: meters, active_energy_kcal: kcal.map { Int($0) }
            )
        }
    }

    /// Map HealthKit's activity type to the small set the backend stores.
    private static func workoutType(_ t: HKWorkoutActivityType) -> String {
        switch t {
        case .running: return "running"
        case .walking, .hiking: return "walking"
        case .cycling: return "cycling"
        case .traditionalStrengthTraining, .functionalStrengthTraining: return "strength"
        case .highIntensityIntervalTraining: return "hiit"
        case .coreTraining, .crossTraining, .flexibility, .yoga, .pilates: return "functional"
        default: return "other"
        }
    }

    // MARK: - Hourly steps — read-only, powers the sit-vs-move pattern

    /// Read per-hour step counts (last 14d) and upsert them — the intraday series we used to discard.
    func syncHourlySteps() async {
        let items = await hourlyStepBuckets()
        guard !items.isEmpty else { return }
        struct Body: Encodable { let hours: [HourlySyncItem] }
        struct Ack: Decodable { let accepted: Int }
        _ = try? await APIClient.shared.post("/api/v1/activity/hourly", body: Body(hours: items)) as Ack
    }

    private func hourlyStepBuckets() async -> [HourlySyncItem] {
        guard let type = HKQuantityType.quantityType(forIdentifier: .stepCount) else { return [] }
        let start = Calendar.current.date(byAdding: .day, value: -14, to: Date()) ?? Date()
        let anchor = Calendar.current.startOfDay(for: start)
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date(), options: .strictStartDate)
        return await withCheckedContinuation { continuation in
            let query = HKStatisticsCollectionQuery(
                quantityType: type, quantitySamplePredicate: predicate,
                options: .cumulativeSum, anchorDate: anchor,
                intervalComponents: DateComponents(hour: 1)
            )
            query.initialResultsHandler = { _, results, _ in
                guard let results else { continuation.resume(returning: []); return }
                var items: [HourlySyncItem] = []
                results.enumerateStatistics(from: start, to: Date()) { stat, _ in
                    let steps = Int(stat.sumQuantity()?.doubleValue(for: .count()) ?? 0)
                    items.append(HourlySyncItem(hour_start: stat.startDate, steps: steps))
                }
                continuation.resume(returning: items)
            }
            store.execute(query)
        }
    }
}

private struct WorkoutSyncItem: Encodable {
    let external_id: String
    let workout_type: String
    let started_at: Date
    let ended_at: Date
    let duration_minutes: Int
    let distance_meters: Double?
    let active_energy_kcal: Int?
}

private struct HourlySyncItem: Encodable {
    let hour_start: Date
    let steps: Int
}

#else

/// Stub used when HealthKit isn't linkable (mirrors the AuthService Firebase-stub pattern).
@MainActor
final class HealthService: ObservableObject {
    @Published private(set) var state: HealthConnectState = .unavailable
    func connectAndSync() async { state = .unavailable }
    func syncLatestSleep() async { state = .unavailable }
    func syncActivity() async {}
    func syncWorkouts() async {}
    func syncHourlySteps() async {}
    func syncBackground() async {}
}

#endif
