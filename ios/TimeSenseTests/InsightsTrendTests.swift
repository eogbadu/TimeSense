import XCTest
@testable import TimeSense

/// TIME-330: the percent charts' scale stops at 100, so a rate outside 0–1 must not draw over the card.
final class InsightsTrendTests: XCTestCase {
    func testRateBecomesAPercent() {
        XCTAssertEqual(WeeklyTrendPoint.percent(0.5), 50)
    }

    func testRateOverOneIsPinnedToTheTop() {
        // A week saved before TIME-330 could report 7 done of 4 added.
        XCTAssertEqual(WeeklyTrendPoint.percent(1.75), 100)
    }

    func testNegativeRateIsPinnedToTheBottom() {
        XCTAssertEqual(WeeklyTrendPoint.percent(-0.2), 0)
    }

    func testNoRateStaysEmpty() {
        XCTAssertNil(WeeklyTrendPoint.percent(nil))
    }
}
