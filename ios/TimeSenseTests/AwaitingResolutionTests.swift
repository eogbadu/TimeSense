import XCTest
@testable import TimeSense

/// TIME-309 — a passed deadline needs a decision, not a louder reminder.
///
/// The user was shown a task due a WEEK earlier as the single best thing to do next, at midnight.
/// The backend demotes those; this covers what the app then SAYS about them, which is the part that
/// has to be right for the card to be worth showing at all.
final class AwaitingResolutionTests: XCTestCase {

    private func item(daysOverdue: Int, title: String = "Ship the thing") -> AwaitingResolution {
        let json = """
        {
          "task": {
            "id": "t1",
            "title": "\(title)",
            "status": "pending",
            "priority": 1,
            "estimated_minutes": 30,
            "due_at": null
          },
          "days_overdue": \(daysOverdue)
        }
        """
        let decoder = JSONDecoder()
        return try! decoder.decode(AwaitingResolution.self, from: Data(json.utf8))
    }

    // MARK: - Decoding

    func testDecodesSnakeCaseKeys() {
        let parsed = item(daysOverdue: 3, title: "Renew the passport")
        XCTAssertEqual(parsed.task.title, "Renew the passport")
        XCTAssertEqual(parsed.daysOverdue, 3)
    }

    func testIdentityComesFromTheTask() {
        XCTAssertEqual(item(daysOverdue: 1).id, "t1")
    }

    // MARK: - The age label
    //
    // This is the sentence that replaces "before 8:00 PM" as the thing the user reads. If it is
    // vague the card is no better than the bug it fixes.

    func testOneDayReadsAsYesterday() {
        XCTAssertEqual(item(daysOverdue: 1).ageLabel, "Due yesterday")
    }

    func testAFewDaysIsPluralised() {
        XCTAssertEqual(item(daysOverdue: 2).ageLabel, "2 days past due")
        XCTAssertEqual(item(daysOverdue: 6).ageLabel, "6 days past due")
    }

    func testTheReportedCaseReadsAsOverAWeek() {
        // Exactly the task the user was shown.
        XCTAssertEqual(item(daysOverdue: 7).ageLabel, "Over a week past due")
    }

    func testTwoWeeksAndBeyondCollapseToWeeks() {
        XCTAssertEqual(item(daysOverdue: 14).ageLabel, "Over 2 weeks past due")
        XCTAssertEqual(item(daysOverdue: 30).ageLabel, "Over 4 weeks past due")
    }

    func testZeroOrNegativeNeverClaimsADayCount() {
        // Defensive: a clock skew or a same-day edge must not render "0 days past due".
        XCTAssertEqual(item(daysOverdue: 0).ageLabel, "Past due")
        XCTAssertEqual(item(daysOverdue: -1).ageLabel, "Past due")
    }

    func testLabelNeverReadsAsAPlainTimeOfDay() {
        // The original bug rendered a week-old deadline as "before 8:00 PM", which reads as tonight.
        // Whatever the age, the label must carry the fact that the deadline has passed.
        for days in [0, 1, 2, 6, 7, 13, 14, 60] {
            let label = item(daysOverdue: days).ageLabel
            XCTAssertTrue(
                label.lowercased().contains("due") || label.lowercased().contains("past"),
                "\(days) days produced \"\(label)\", which doesn't say the deadline passed"
            )
            XCTAssertFalse(label.contains("AM") || label.contains("PM"),
                           "\(days) days produced a bare clock time: \"\(label)\"")
        }
    }
}
