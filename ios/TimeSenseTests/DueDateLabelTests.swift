import XCTest
@testable import TimeSense

/// TIME-310 — a week-old deadline rendered as "before 8:00 PM", reading as tonight.
///
/// The Today card formatted every deadline with `date: .omitted`, so the date was ALWAYS dropped.
/// The user could not tell the deadline had passed, let alone by how much — which was exactly the
/// information that would have explained the recommendation they were questioning.
final class DueDateLabelTests: XCTestCase {

    /// A fixed calendar so these never depend on the machine's locale or the day they run.
    private var cal: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "America/New_York")!
        c.locale = Locale(identifier: "en_US")
        return c
    }()

    private func date(_ year: Int, _ month: Int, _ day: Int, _ hour: Int = 20, _ minute: Int = 0) -> Date {
        cal.date(from: DateComponents(year: year, month: month, day: day, hour: hour, minute: minute))!
    }

    private var now: Date { date(2026, 8, 30, 0, 3) }   // 12:03 AM — when the bug was reported

    /// iOS renders "8:00 PM" with a NARROW NO-BREAK SPACE before the meridiem, so a hardcoded
    /// literal never matches. Derive the expected substring the same way the label does.
    private func time(_ d: Date) -> String { DueDateLabel.shortTime(d, cal) }

    // MARK: - The bug

    func testAWeekOldDeadlineDoesNotRenderAsABareTime() {
        let r = DueDateLabel.render(date(2026, 8, 23), now: now, calendar: cal)
        XCTAssertTrue(r.isOverdue)
        XCTAssertFalse(r.text.hasPrefix("before "),
                       "a passed deadline must not read like an upcoming one: \(r.text)")
        XCTAssertTrue(r.text.contains("Aug 23"), "expected a real date, got \(r.text)")
    }

    func testYesterdaysDeadlineSaysYesterday() {
        let r = DueDateLabel.render(date(2026, 8, 29), now: now, calendar: cal)
        XCTAssertEqual(r.text, "Was due yesterday")
        XCTAssertTrue(r.isOverdue)
    }

    func testAFewDaysLateCountsTheDays() {
        XCTAssertEqual(DueDateLabel.render(date(2026, 8, 27), now: now, calendar: cal).text,
                       "Was due 3 days ago")
    }

    func testPastAWeekSwitchesToARealDate() {
        // "8 days ago" stops being meaningful; a date is easier to act on.
        XCTAssertEqual(DueDateLabel.render(date(2026, 8, 22), now: now, calendar: cal).text,
                       "Was due Aug 22")
    }

    // MARK: - What must NOT change

    func testADeadlineLaterTodayKeepsTheBareTime() {
        let r = DueDateLabel.render(date(2026, 8, 30, 20), now: now, calendar: cal)
        XCTAssertEqual(r.text, "before \(time(date(2026, 8, 30, 20)))")
        XCTAssertFalse(r.isOverdue)
    }

    func testADeadlineEarlierTodayIsNotYetOverdue() {
        // Matches the backend rule (TIME-309): staleness is judged by DAY, not instant. A task due
        // at 8pm must not turn red at 8:05pm while the user is still working on it.
        let evening = date(2026, 8, 30, 20)
        let justAfter = date(2026, 8, 30, 20, 5)
        XCTAssertFalse(DueDateLabel.isOverdue(evening, now: justAfter, calendar: cal))
        XCTAssertEqual(DueDateLabel.render(evening, now: justAfter, calendar: cal).text,
                       "before \(time(evening))")
    }

    // MARK: - Future deadlines gain the date they were missing

    func testTomorrowIsNamed() {
        let tomorrow = date(2026, 8, 31)
        XCTAssertEqual(DueDateLabel.render(tomorrow, now: now, calendar: cal).text,
                       "before tomorrow, \(time(tomorrow))")
    }

    func testWithinTheWeekUsesTheWeekday() {
        let due = date(2026, 9, 2)
        let text = DueDateLabel.render(due, now: now, calendar: cal).text
        XCTAssertEqual(text, "before \(DueDateLabel.weekday(due, cal)), \(time(due))")
        // The point of the case: the weekday, not just a clock time.
        XCTAssertTrue(text.contains(DueDateLabel.weekday(due, cal)), "got \(text)")
    }

    func testBeyondTheWeekUsesTheDate() {
        let text = DueDateLabel.render(date(2026, 9, 15), now: now, calendar: cal).text
        XCTAssertTrue(text.contains("Sep 15"), "got \(text)")
    }

    // MARK: - Invariants

    func testOnlyPastDeadlinesAreFlaggedOverdue() {
        for day in 23...29 {
            XCTAssertTrue(DueDateLabel.isOverdue(date(2026, 8, day), now: now, calendar: cal),
                          "Aug \(day) should be overdue at Aug 30")
        }
        for day in 30...31 {
            XCTAssertFalse(DueDateLabel.isOverdue(date(2026, 8, day), now: now, calendar: cal),
                           "Aug \(day) should not be overdue at Aug 30")
        }
    }

    func testNoFutureDeadlineIsEverAmbiguousAboutItsDay() {
        // The original defect in one assertion: any deadline that is not today must carry something
        // beyond a clock time.
        for offset in 1...30 {
            let due = cal.date(byAdding: .day, value: offset, to: now)!
            let text = DueDateLabel.render(due, now: now, calendar: cal).text
            XCTAssertNotEqual(text, "before \(time(due))",
                              "+\(offset) days rendered as a bare time: \(text)")
        }
    }
}
