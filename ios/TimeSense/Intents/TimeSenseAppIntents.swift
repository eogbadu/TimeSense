import AppIntents
import Foundation

// MARK: - App Intents
//
// Each intent calls the app's single network path (APIClient.shared). Read-only and simple-write
// actions run headless (no app launch); ReplanDay opens the app because replans always require
// explicit in-app approval — never auto-applied. If the user isn't authenticated (APIClient has no
// token), the backend returns 401 and the intent surfaces a friendly error dialog.

// MARK: What to do next

struct WhatToDoNextIntent: AppIntent {
    static var title: LocalizedStringResource = "What to do next"
    static var description = IntentDescription("Ask TimeSense what to focus on right now.")
    static var openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        do {
            let ctx: NowContext = try await APIClient.shared.get("/api/v1/now")
            guard let task = ctx.bestTask else {
                return .result(dialog: "You're all caught up — nothing on your plate right now.")
            }
            return .result(dialog: IntentDialog(
                "Do \(task.title) next. You have \(ctx.usableMinutes) minutes of usable time."
            ))
        } catch {
            return .result(dialog: IntentDialog(stringLiteral: friendlyMessage(error)))
        }
    }
}

// MARK: Log lunch

struct LogLunchIntent: AppIntent {
    static var title: LocalizedStringResource = "Log lunch"
    static var description = IntentDescription("Record that you've eaten lunch.")
    static var openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        struct MealLog: Encodable { let meal_type: String; let status: String }
        struct MealResponse: Decodable { let meal_type: String; let status: String }
        do {
            let _: MealResponse = try await APIClient.shared.post(
                "/api/v1/meals", body: MealLog(meal_type: "lunch", status: "eaten")
            )
            return .result(dialog: "Logged your lunch.")
        } catch {
            return .result(dialog: IntentDialog(stringLiteral: friendlyMessage(error)))
        }
    }
}

// MARK: Start focus

struct StartFocusIntent: AppIntent {
    static var title: LocalizedStringResource = "Start focus"
    static var description = IntentDescription("Start a focus session on your best next task.")
    static var openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        do {
            let ctx: NowContext = try await APIClient.shared.get("/api/v1/now")
            guard let task = ctx.bestTask else {
                return .result(dialog: "Nothing to focus on right now — you're all caught up.")
            }
            return .result(dialog: IntentDialog("Focusing on \(task.title). Let's go."))
        } catch {
            return .result(dialog: IntentDialog(stringLiteral: friendlyMessage(error)))
        }
    }
}

// MARK: Mark done

struct MarkDoneIntent: AppIntent {
    static var title: LocalizedStringResource = "Mark done"
    static var description = IntentDescription("Mark your current best task as done.")
    static var openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        struct StatusUpdate: Encodable { let status: String }
        struct TaskPatchResponse: Decodable { let id: String }
        do {
            let ctx: NowContext = try await APIClient.shared.get("/api/v1/now")
            guard let task = ctx.bestTask else {
                return .result(dialog: "There's nothing to mark done right now.")
            }
            let _: TaskPatchResponse = try await APIClient.shared.patch(
                "/api/v1/tasks/\(task.id)", body: StatusUpdate(status: "done")
            )
            return .result(dialog: IntentDialog("Nice — marked \(task.title) as done."))
        } catch {
            return .result(dialog: IntentDialog(stringLiteral: friendlyMessage(error)))
        }
    }
}

// MARK: Replan day

struct ReplanDayIntent: AppIntent {
    static var title: LocalizedStringResource = "Replan my day"
    static var description = IntentDescription("Open TimeSense to review and approve a new plan.")
    // Replans always require explicit approval, so this opens the app rather than acting headlessly.
    static var openAppWhenRun = true

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        return .result(dialog: "Opening TimeSense so you can review and approve your new plan.")
    }
}

// MARK: - Shared error copy

private func friendlyMessage(_ error: Error) -> String {
    if let apiError = error as? APIError {
        switch apiError {
        case .unauthorized:
            return "Please open TimeSense and sign in first."
        default:
            return apiError.errorDescription ?? "Something went wrong. Try again in the app."
        }
    }
    return "Something went wrong. Try again in the app."
}
