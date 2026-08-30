import Foundation

/// How a deadline reads on a card (TIME-310).
///
/// The Today card rendered every deadline with `due.formatted(date: .omitted, time: .shortened)`,
/// which ALWAYS drops the date. A task that had been due a week earlier displayed as
/// "before 8:00 PM" — reading as tonight. The user could not tell from the card that the deadline
/// had passed, let alone by how much, which was precisely the information that would have explained
/// why the app was recommending it.
///
/// This lives in a value type rather than inside the view on purpose. TIME-306 was a display bug
/// that `BUILD SUCCEEDED` and a store-level test both missed, because the fault sat in logic that
/// only existed inside a SwiftUI view and so could not be called from a test. Anything a card
/// asserts to the user belongs somewhere a test can reach.
enum DueDateLabel {

    /// What the card says, and whether it should be styled as a warning.
    struct Rendered: Equatable {
        let text: String
        let isOverdue: Bool
    }

    /// A deadline is "overdue" once its local DAY is behind today's — matching the backend's
    /// `is_awaiting_resolution` (TIME-309). Deliberately not `due < now`: a task due at 8pm should
    /// not flip to a red warning at 8:05pm while the user is still working on it.
    static func isOverdue(_ due: Date, now: Date = Date(), calendar: Calendar = .current) -> Bool {
        dayDelta(due, now, calendar) < 0
    }

    static func render(_ due: Date, now: Date = Date(), calendar: Calendar = .current) -> Rendered {
        let days = dayDelta(due, now, calendar)

        if days < 0 {
            return Rendered(text: overdueText(due, daysLate: -days, calendar: calendar), isOverdue: true)
        }

        let time = shortTime(due, calendar)
        switch days {
        case 0:
            // Unchanged from before, and unambiguous: a bare time on the day it's due reads correctly.
            return Rendered(text: "before \(time)", isOverdue: false)
        case 1:
            return Rendered(text: "before tomorrow, \(time)", isOverdue: false)
        case 2...6:
            // Within the week, the weekday is the most useful handle ("before Thu, 8:00 PM").
            return Rendered(text: "before \(weekday(due, calendar)), \(time)", isOverdue: false)
        default:
            return Rendered(text: "before \(monthDay(due, calendar)), \(time)", isOverdue: false)
        }
    }

    /// Convenience for callers that only need the string.
    static func text(_ due: Date, now: Date = Date(), calendar: Calendar = .current) -> String {
        render(due, now: now, calendar: calendar).text
    }

    // MARK: - Private

    /// Whole calendar days from today to the deadline's day. Negative when the deadline has passed.
    ///
    /// Counted in DAYS rather than elapsed hours so the label matches how the deadline reads to the
    /// user: something due at 8pm yesterday is "yesterday", not "0 days" because 14 hours have passed.
    private static func dayDelta(_ due: Date, _ now: Date, _ calendar: Calendar) -> Int {
        let from = calendar.startOfDay(for: now)
        let to = calendar.startOfDay(for: due)
        return calendar.dateComponents([.day], from: from, to: to).day ?? 0
    }

    private static func overdueText(_ due: Date, daysLate: Int, calendar: Calendar) -> String {
        switch daysLate {
        case 1:
            return "Was due yesterday"
        case 2...6:
            return "Was due \(daysLate) days ago"
        default:
            // Past a week, "8 days ago" stops being meaningful and a real date is easier to act on.
            return "Was due \(monthDay(due, calendar))"
        }
    }

    // Formatting goes through the SAME calendar the day arithmetic uses. Date.formatted() silently
    // uses the device's timezone and locale instead, which made the label disagree with its own
    // overdue calculation whenever the two differed — and made these untestable, since a test can
    // pass a calendar but cannot change the device.

    private static func formatter(_ calendar: Calendar, template: String) -> DateFormatter {
        let f = DateFormatter()
        f.calendar = calendar
        f.timeZone = calendar.timeZone
        f.locale = calendar.locale ?? .current
        f.setLocalizedDateFormatFromTemplate(template)
        return f
    }

    static func shortTime(_ date: Date, _ calendar: Calendar) -> String {
        let f = DateFormatter()
        f.calendar = calendar
        f.timeZone = calendar.timeZone
        f.locale = calendar.locale ?? .current
        f.timeStyle = .short
        f.dateStyle = .none
        return f.string(from: date)
    }

    static func weekday(_ date: Date, _ calendar: Calendar) -> String {
        formatter(calendar, template: "EEE").string(from: date)
    }

    static func monthDay(_ date: Date, _ calendar: Calendar) -> String {
        formatter(calendar, template: "MMMd").string(from: date)
    }
}
