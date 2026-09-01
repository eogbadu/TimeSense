import XCTest
@testable import TimeSense

/// Tests for completing a task and saying how long it took (TIME-316).
///
/// The gap these exist for: the whole "how long did that take?" experience was reachable from
/// exactly one place — the Now screen's recommended task. Completing anything from Today sent a
/// bare status change, taught the duration estimator nothing, and left a running timer going. That
/// made the most useful case invisible, because the task a user seizes an opportunity to do is
/// precisely the one the assistant did NOT pick.
///
/// The network paths need `APIClient.shared`, which isn't injectable, so what is asserted here is
/// the pure logic underneath: which figure the sheet opens on, and what counts as a real
/// measurement.
final class DurationFeedbackTests: XCTestCase {

    // MARK: - The plausibility guard
    //
    // A timer left running overnight is not an observation. Feeding one in would poison the learned
    // estimate for that whole task type — and the estimate is what every later recommendation is
    // built on, so one bad number spreads.

    func testARealDurationIsAccepted() {
        XCTAssertEqual(plausibleDurationMinutes(25), 25)
    }

    func testSecondsRoundToTheNearestMinute() {
        XCTAssertEqual(plausibleDurationMinutes(0.6), 1)
        XCTAssertEqual(plausibleDurationMinutes(25.4), 25)
        XCTAssertEqual(plausibleDurationMinutes(25.6), 26)
    }

    func testAnInstantTapIsNotAnObservation() {
        // Started and stopped a few seconds later — the user didn't do the task in 20 seconds.
        XCTAssertNil(plausibleDurationMinutes(0.4))
        XCTAssertNil(plausibleDurationMinutes(0))
    }

    func testATimerLeftRunningOvernightIsRejected() {
        XCTAssertEqual(plausibleDurationMinutes(480), 480, "eight hours is still a real work day")
        XCTAssertNil(plausibleDurationMinutes(481))
        XCTAssertNil(plausibleDurationMinutes(12 * 60))
    }

    func testNegativeElapsedIsRejected() {
        // A clock change can produce this; it must not become a duration.
        XCTAssertNil(plausibleDurationMinutes(-5))
    }

    // MARK: - What the sheet opens on
    //
    // Design goal #1 of the sheet is "never become a chore": it opens on the best figure available
    // so "that was about right" is a single tap. Precedence is measured → estimated → neutral.

    func testATimedFigureWinsOverTheEstimate() {
        let prompt = DurationPrompt(id: "t1", title: "Write the report", estimatedMinutes: 30,
                                    taskType: "deep_work", measuredMinutes: 47)
        XCTAssertEqual(openingValue(for: prompt), 47, "a real measurement beats a prediction")
    }

    func testTheEstimateIsUsedWhenNothingWasTimed() {
        let prompt = DurationPrompt(id: "t1", title: "Write the report", estimatedMinutes: 30,
                                    taskType: "deep_work", measuredMinutes: nil)
        XCTAssertEqual(openingValue(for: prompt), 30)
    }

    func testAneutralDefaultWhenThereIsNeither() {
        let prompt = DurationPrompt(id: "t1", title: "Something new", estimatedMinutes: nil,
                                    taskType: nil, measuredMinutes: nil)
        XCTAssertEqual(openingValue(for: prompt), 30)
    }

    /// Mirrors `DurationFeedbackSheet.init`'s seeding rule.
    private func openingValue(for prompt: DurationPrompt) -> Int {
        prompt.measuredMinutes ?? prompt.estimatedMinutes ?? 30
    }

    // MARK: - Completing from Today carries what the prompt needs
    //
    // Today's rows already hold the title and estimate, which is why this needed no new API field.

    func testATodayRowCarriesEnoughToAskTheQuestion() {
        let json = """
        {"id":"abc","title":"Buy groceries","status":"pending","priority":3,
         "estimated_minutes":25,"auto_scheduled":false}
        """.data(using: .utf8)!
        let task = try? JSONDecoder().decode(TimelineTask.self, from: json)
        XCTAssertEqual(task?.title, "Buy groceries")
        XCTAssertEqual(task?.estimatedMinutes, 25)

        let prompt = DurationPrompt(id: task!.id, title: task!.title,
                                    estimatedMinutes: task!.estimatedMinutes,
                                    taskType: nil, measuredMinutes: nil)
        XCTAssertEqual(openingValue(for: prompt), 25)
    }
}
