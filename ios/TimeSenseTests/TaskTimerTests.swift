import XCTest
@testable import TimeSense

/// Tests for the task timer.
///
/// This target exists because of these two bugs specifically. Both reached the user's phone, both
/// were "verified" by BUILD SUCCEEDED, and neither could have been caught that way:
///
///   TIME-298 — the timer forgot it was running when the view was recreated or the app restarted.
///   TIME-306 — the label rendered 0:00 forever, because the view received elapsed time as a value
///              from its parent (frozen at the parent's last render) rather than deriving it.
///
/// So the tests below assert the two properties those bugs violated: the label must ADVANCE with
/// the clock, and a running timer must SURVIVE a restart.
final class TaskTimerTests: XCTestCase {

    private func timer(
        startedMinutesAgo: Double = 0,
        estimate: Int? = 30,
        acknowledged: Bool = false
    ) -> RunningTaskTimer {
        RunningTaskTimer(
            taskId: "task-1",
            taskTitle: "Write the report",
            startedAt: Date().addingTimeInterval(-startedMinutesAgo * 60),
            estimatedMinutes: estimate,
            overrunAcknowledged: acknowledged
        )
    }

    // MARK: - TIME-306: the label must advance

    func testLabelAdvancesWithTheClock() {
        let t = timer()
        let labels = [0.0, 1.0, 2.0, 59.0, 60.0, 3661.0].map { t.label(at: t.startedAt.addingTimeInterval($0)) }

        XCTAssertEqual(labels, ["0:00", "0:01", "0:02", "0:59", "1:00", "1:01:01"])
        XCTAssertEqual(Set(labels).count, labels.count, "every tick must render a distinct value")
    }

    func testLabelIsNeverFrozenAtZero() {
        // The exact shape of the shipped bug: a label computed once and never recomputed.
        let t = timer()
        let later = t.label(at: t.startedAt.addingTimeInterval(90))
        XCTAssertNotEqual(later, "0:00", "the label must not be stuck at its initial value")
        XCTAssertEqual(later, "1:30")
    }

    func testLabelShowsSecondsBeforeTheFirstMinute() {
        // The original complaint: nothing moved for a whole minute.
        let t = timer()
        XCTAssertEqual(t.label(at: t.startedAt.addingTimeInterval(5)), "0:05")
    }

    // MARK: - TIME-298: elapsed derives from the start timestamp

    func testElapsedIsDerivedFromTheStartTimestampNotAccumulated() {
        // Deriving from a timestamp is what makes backgrounding and suspension safe.
        let t = timer(startedMinutesAgo: 2)
        XCTAssertEqual(t.elapsed, 120, accuracy: 2)
        XCTAssertEqual(t.elapsedMinutes, 2)
    }

    func testARunningTimerSurvivesARestart() {
        // A restart means the process is gone: only what was encoded survives.
        let original = timer(startedMinutesAgo: 3)
        let data = try! JSONEncoder().encode(original)
        let restored = try! JSONDecoder().decode(RunningTaskTimer.self, from: data)

        XCTAssertEqual(restored.taskId, original.taskId)
        XCTAssertEqual(restored.startedAt.timeIntervalSince1970,
                       original.startedAt.timeIntervalSince1970, accuracy: 0.001)
        XCTAssertEqual(restored.elapsed, 180, accuracy: 2, "it must keep counting across a restart")
        XCTAssertEqual(restored.label(at: restored.startedAt.addingTimeInterval(180)), "3:00")
    }

    // MARK: - TIME-299: the overrun prompt

    func testOverrunFiresAfterTheEstimatePlusGrace() {
        XCTAssertFalse(timer(startedMinutesAgo: 30, estimate: 30).isOverrunning)
        XCTAssertFalse(timer(startedMinutesAgo: 59, estimate: 30).isOverrunning)
        XCTAssertTrue(timer(startedMinutesAgo: 61, estimate: 30).isOverrunning)
    }

    func testTheGraceScalesWithTheEstimate() {
        // A two-hour task must not be nagged at the same point as a five-minute one.
        XCTAssertFalse(timer(startedMinutesAgo: 100, estimate: 120).isOverrunning)
        XCTAssertTrue(timer(startedMinutesAgo: 151, estimate: 120).isOverrunning)
        XCTAssertTrue(timer(startedMinutesAgo: 36, estimate: 5).isOverrunning)
    }

    func testAMissingEstimateFallsBackRatherThanNeverPrompting() {
        let t = timer(startedMinutesAgo: 61, estimate: nil)
        XCTAssertEqual(t.expectedMinutes, RunningTaskTimer.fallbackEstimateMinutes)
        XCTAssertTrue(t.isOverrunning)
    }

    func testTheUserIsAskedOnceNotRepeatedly() {
        XCTAssertTrue(timer(startedMinutesAgo: 61).needsOverrunPrompt)
        XCTAssertFalse(timer(startedMinutesAgo: 61, acknowledged: true).needsOverrunPrompt,
                       "answering once must silence it — the product rule is no nagging")
    }

    func testAcknowledgementSurvivesARestart() {
        let acked = timer(startedMinutesAgo: 61, acknowledged: true)
        let restored = try! JSONDecoder().decode(
            RunningTaskTimer.self, from: try! JSONEncoder().encode(acked))
        XCTAssertFalse(restored.needsOverrunPrompt)
    }

    // MARK: - formatting edges

    func testFormattingEdges() {
        XCTAssertEqual(formatElapsed(0), "0:00")
        XCTAssertEqual(formatElapsed(-10), "0:00", "a negative interval must not render as garbage")
        XCTAssertEqual(formatElapsed(3599), "59:59")
        XCTAssertEqual(formatElapsed(3600), "1:00:00")
    }

    func testAnAbandonedTimerIsNotRestorable() {
        // Started and forgotten overnight: it cannot produce a usable observation, and showing it
        // would present the user with a nonsense number.
        XCTAssertGreaterThan(timer(startedMinutesAgo: 13 * 60).elapsed,
                             TaskTimerStore.maxRestorableAge)
        XCTAssertLessThan(timer(startedMinutesAgo: 90).elapsed,
                          TaskTimerStore.maxRestorableAge)
    }
}
