import Foundation
import WidgetKit

/// Just enough of another task to name it: what a task waits for (TIME-327).
struct TaskRef: Decodable, Hashable, Identifiable {
    let id: String
    let title: String
}

struct TimelineTask: Decodable, Identifiable {
    let id: String
    let title: String
    let status: String
    let scheduledStart: Date?
    let scheduledEnd: Date?
    let estimatedMinutes: Int?
    let priority: Int
    let autoScheduled: Bool
    // Steps and waits (TIME-327). All optional, so a response from before they existed still decodes.
    let parentTaskId: String?
    let parentTitle: String?
    /// Place in the group's order, counting every step the group has ever had. Used to move a step.
    let position: Int?
    let stepNumber: Int?
    let parentStepCount: Int?
    let stepCount: Int?
    let openStepCount: Int?
    let blockedBy: [TaskRef]?
    let steps: [TimelineTask]?

    enum CodingKeys: String, CodingKey {
        case id, title, status, priority, steps, position
        case scheduledStart = "scheduled_start"
        case scheduledEnd = "scheduled_end"
        case estimatedMinutes = "estimated_minutes"
        case autoScheduled = "auto_scheduled"
        case parentTaskId = "parent_task_id"
        case parentTitle = "parent_title"
        case stepNumber = "step_number"
        case parentStepCount = "parent_step_count"
        case stepCount = "step_count"
        case openStepCount = "open_step_count"
        case blockedBy = "blocked_by"
    }

    /// The steps nested under this task in the plan, in order. Empty for an ordinary task.
    var groupSteps: [TimelineTask] { steps ?? [] }
    var isGroup: Bool { !groupSteps.isEmpty }
    var doneStepCount: Int { groupSteps.filter { $0.status == "done" }.count }
    var openSteps: [TimelineTask] { groupSteps.filter { $0.status != "done" && $0.status != "cancelled" } }
    var waitsFor: [TaskRef] { blockedBy ?? [] }
    /// Still waiting on something unfinished. A finished task is never shown as waiting.
    var isWaiting: Bool { status != "done" && !waitsFor.isEmpty }
}

/// One row of the unified Smart Plan: an actionable `task`, or a read-only calendar `event` block.
struct TimelineEntry: Decodable, Identifiable {
    let kind: String            // "task" | "event"
    let id: String
    let title: String
    let start: Date?
    let end: Date?
    let location: String?
    let task: TimelineTask?     // present when kind == "task"

    var isEvent: Bool { kind == "event" }
}

/// "Break this down": steps TimeSense suggests for a task. Nothing is saved until the user keeps some
/// (TIME-325/328).
struct StepSuggestions: Decodable {
    struct Draft: Decodable, Hashable {
        let title: String
        let estimatedMinutes: Int?

        enum CodingKeys: String, CodingKey {
            case title
            case estimatedMinutes = "estimated_minutes"
        }
    }

    /// False when TimeSense couldn't come up with anything, rather than "this is already one step".
    let available: Bool
    let steps: [Draft]
    let sequential: Bool
}

/// How steps and waits are worded and chosen, kept in one place so Now, Today and Siri say the same
/// thing (TIME-327). Pure functions, so they are tested without a screen.
enum StepLabels {
    /// "RENEW PASSPORT · STEP 1 OF 3", above a step's title. A step alone ("Get photos") doesn't say
    /// what it is for.
    static func eyebrow(parentTitle: String?, stepNumber: Int?, stepCount: Int?) -> String? {
        guard let parent = parentTitle?.trimmingCharacters(in: .whitespaces), !parent.isEmpty else {
            return nil
        }
        guard let number = stepNumber, let total = stepCount, total > 0 else { return parent.uppercased() }
        return "\(parent.uppercased()) · STEP \(number) OF \(total)"
    }

    /// The same eyebrow for VoiceOver, which would otherwise spell out the capitals.
    static func spokenEyebrow(parentTitle: String?, stepNumber: Int?, stepCount: Int?) -> String? {
        guard let parent = parentTitle, !parent.isEmpty else { return nil }
        guard let number = stepNumber, let total = stepCount, total > 0 else { return "Part of \(parent)" }
        return "Step \(number) of \(total), part of \(parent)"
    }

    /// "After: Get invoice", or "After: Get invoice + 1 more".
    static func waitingCaption(_ refs: [TaskRef]) -> String? {
        guard let first = refs.first else { return nil }
        return refs.count == 1 ? "After: \(first.title)" : "After: \(first.title) + \(refs.count - 1) more"
    }

    /// "1 of 3 steps" on a group row.
    static func progress(done: Int, total: Int) -> String {
        "\(done) of \(total) step\(total == 1 ? "" : "s")"
    }

    /// Asked before finishing a group that still has open steps, because it finishes them too.
    static func completeGroupPrompt(openSteps: Int) -> String {
        openSteps == 1 ? "Mark the last step done too?" : "Mark all \(openSteps) remaining steps done?"
    }

    /// "Get photos, for Renew passport", as Siri says it.
    static func spoken(title: String, parentTitle: String?) -> String {
        guard let parent = parentTitle, !parent.isEmpty else { return title }
        return "\(title), for \(parent)"
    }

    /// The waits on a step the user can remove with "Don't wait". The step's order in its group and
    /// the waits it inherits from its parent aren't its own, so removing them on the step would fail.
    static func removableWaits(for step: TimelineTask, in group: TimelineTask) -> [TaskRef] {
        let siblings = Set(group.groupSteps.map(\.id))
        let inherited = Set(group.waitsFor.map(\.id))
        return step.waitsFor.filter { !siblings.contains($0.id) && !inherited.contains($0.id) }
    }

    /// What the "what would you rather do?" picker offers: a group's open steps rather than the group,
    /// and nothing that is still waiting on something else.
    static func swapCandidates(from entries: [TimelineEntry], excluding taskId: String) -> [TimelineTask] {
        allTasks(in: entries).filter { task in
            task.id != taskId && isOpen(task) && !task.isWaiting && !task.isGroup
        }
    }

    // MARK: - Looking tasks up (TIME-328)

    static func isOpen(_ task: TimelineTask) -> Bool {
        task.status != "done" && task.status != "cancelled"
    }

    /// Every task in the plan, in order, with each group's steps directly after it.
    static func allTasks(in entries: [TimelineEntry]) -> [TimelineTask] {
        entries.compactMap(\.task).flatMap { [$0] + $0.groupSteps }
    }

    static func findTask(_ id: String, in entries: [TimelineEntry]) -> TimelineTask? {
        allTasks(in: entries).first { $0.id == id }
    }

    static func group(containing step: TimelineTask, in entries: [TimelineEntry]) -> TimelineTask? {
        guard let parentId = step.parentTaskId else { return nil }
        return entries.compactMap(\.task).first { $0.id == parentId }
    }

    // MARK: - Pickers (TIME-328)

    /// What `task` could be made to wait for. Excluded: itself; anything it already waits for; its own
    /// group or steps, which the server refuses; anything that already waits on it, which would loop;
    /// and finished work. The server still checks longer loops.
    static func waitCandidates(for task: TimelineTask, in entries: [TimelineEntry]) -> [TimelineTask] {
        var excluded = Set([task.id] + task.waitsFor.map(\.id) + task.groupSteps.map(\.id))
        if let parent = task.parentTaskId { excluded.insert(parent) }
        return allTasks(in: entries).filter { other in
            !excluded.contains(other.id) && isOpen(other) && !other.waitsFor.contains { $0.id == task.id }
        }
    }

    /// What `task` could become a step of: an open task that isn't a step itself, other than `task` and
    /// its current group. A task that has steps of its own can't become a step, so it gets nothing.
    static func parentCandidates(for task: TimelineTask, in entries: [TimelineEntry]) -> [TimelineTask] {
        guard !task.isGroup else { return [] }
        return entries.compactMap(\.task).filter { other in
            other.id != task.id && other.id != task.parentTaskId && other.parentTaskId == nil && isOpen(other)
        }
    }

    /// Case-insensitive search by title, or by the group a step belongs to.
    static func search(_ tasks: [TimelineTask], for query: String) -> [TimelineTask] {
        let q = query.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return tasks }
        return tasks.filter {
            $0.title.localizedCaseInsensitiveContains(q)
                || ($0.parentTitle?.localizedCaseInsensitiveContains(q) ?? false)
        }
    }

    /// The second line of a picker row: how far along a group is, or which group a step is in.
    static func pickerDetail(for task: TimelineTask) -> String? {
        if task.isGroup { return progress(done: task.doneStepCount, total: task.groupSteps.count) }
        if let parent = task.parentTitle, !parent.isEmpty { return "Part of \(parent)" }
        return nil
    }

    /// The server's own sentence for a refusal ("That would make these tasks wait on each other."), or
    /// a calm fallback. FastAPI sends `{"detail": "…"}`; request validation sends a list instead, which
    /// isn't meant for people.
    static func message(for error: Error) -> String {
        var body: Data?
        if let apiError = error as? APIError {
            switch apiError {
            case .serverError(_, let data), .validationError(let data): body = data
            default: break
            }
        }
        struct Detail: Decodable { let detail: String }
        if let body, let decoded = try? JSONDecoder().decode(Detail.self, from: body),
           !decoded.detail.isEmpty {
            return decoded.detail
        }
        return "That didn't work. Please try again."
    }
}

enum TodayUiState {
    case idle
    case loading
    case loaded([TimelineEntry])
    case error(String)
}

@MainActor
final class TodayViewModel: ObservableObject, DurationPrompting {
    @Published var uiState: TodayUiState = .idle
    /// Raised after completing a task, while the assistant is still learning that type (TIME-316).
    @Published var durationPrompt: DurationPrompt?
    /// The current best-next-action (same as Now) — shown in the "AI Recommended Now" card.
    @Published var recommendation: NowContext?

    var entries: [TimelineEntry] {
        if case .loaded(let items) = uiState { return items }
        return []
    }

    /// Just the actionable task entries (calendar events are read-only and don't count toward totals).
    var tasks: [TimelineTask] { entries.compactMap { $0.task } }

    var doneCount: Int { tasks.filter { $0.status == "done" }.count }

    /// Any task in today's plan by id, including a step inside a group.
    func task(withId id: String) -> TimelineTask? { StepLabels.findTask(id, in: entries) }

    /// The group a step belongs to, when that group is in today's plan.
    func group(containing step: TimelineTask) -> TimelineTask? {
        StepLabels.group(containing: step, in: entries)
    }

    /// Lazily fetch the structured explanation for the recommended task.
    func fetchExplanation(taskId: String) async -> RecommendationExplanation? {
        return try? await APIClient.shared.get("/api/v1/now/why?task_id=\(taskId)")
    }

    /// Complete a task from today's plan — whichever one it is, recommended or not.
    ///
    /// Until TIME-316 this sent a bare status change: no "how long did that take?", and a timer
    /// left running. That made the most useful case invisible, because the task the user seizes an
    /// opportunity to do is precisely the one the assistant did NOT pick.
    func markDone(task: TimelineTask) async {
        // The row's circle stays tappable once a task is done; re-completing it would re-ask how
        // long it took, which is a nag.
        guard task.status != "done" else { return }
        await completeAndMaybeAskDuration(taskId: task.id, title: task.title,
                                          estimatedMinutes: task.estimatedMinutes)
        await load()
    }

    /// Finish a whole group. The server closes its open steps too (TIME-321). There's no "how long did
    /// that take?": the steps were the work, and the group as a whole teaches nothing about a type of
    /// task. The view confirms first when steps are still open.
    func completeGroup(_ group: TimelineTask) async {
        guard group.status != "done" else { return }
        struct StatusUpdate: Encodable { let status: String }
        let _: IDOnly? = try? await APIClient.shared.patch(
            "/api/v1/tasks/\(group.id)", body: StatusUpdate(status: "done")
        )
        for step in group.groupSteps { TaskTimerStore.shared.stopIfTiming(taskId: step.id) }
        await load()
    }

    // MARK: - Shaping a task (TIME-327/328)
    //
    // Each returns nil on success, or the sentence to show the user when the server refuses. The plan
    // is reloaded either way, so the screen always shows what is really there.

    /// "Add a step" from a context menu: one new step at the end.
    @discardableResult
    func addStep(to parent: TimelineTask, title: String) async -> String? {
        await addSteps(to: parent, drafts: [.init(title: title, estimatedMinutes: nil)])
    }

    /// New steps at the end of `parent`'s steps. `sequential` sets whether the group happens in order;
    /// nil keeps it as it is.
    @discardableResult
    func addSteps(to parent: TimelineTask, drafts: [StepSuggestions.Draft],
                  sequential: Bool? = nil) async -> String? {
        let steps = drafts.compactMap { draft -> StepsBody.Step? in
            let title = draft.title.trimmingCharacters(in: .whitespacesAndNewlines)
            return title.isEmpty ? nil : StepsBody.Step(title: title, estimated_minutes: draft.estimatedMinutes)
        }
        guard !steps.isEmpty else { return nil }
        return await perform {
            let _: IDOnly = try await APIClient.shared.post(
                "/api/v1/tasks/\(parent.id)/steps", body: StepsBody(steps: steps, sequential: sequential)
            )
        }
    }

    /// "Break this down": suggested steps, nothing saved. Nil when the request itself failed.
    func breakdown(_ task: TimelineTask) async -> StepSuggestions? {
        struct Empty: Encodable {}
        return try? await APIClient.shared.post("/api/v1/tasks/\(task.id)/breakdown", body: Empty())
    }

    /// "Make it a step of…": `task` joins `parent`, at the end.
    @discardableResult
    func makeStep(_ task: TimelineTask, of parent: TimelineTask) async -> String? {
        struct Body: Encodable { let parent_task_id: String }
        return await perform {
            let _: IDOnly = try await APIClient.shared.patch(
                "/api/v1/tasks/\(task.id)", body: Body(parent_task_id: parent.id)
            )
        }
    }

    /// Where a step that just joined an ordered group probably belongs: the step it should come before,
    /// or nil for "at the end", an unordered group, or no suggestion.
    func suggestedPlace(for stepId: String, in parentId: String) async -> TaskRef? {
        struct Resp: Decodable {
            let before_step_id: String?
            let before_step_title: String?
        }
        guard let resp: Resp = try? await APIClient.shared.get(
                  "/api/v1/tasks/\(stepId)/step-position?parent_id=\(parentId)"),
              let id = resp.before_step_id, let title = resp.before_step_title else { return nil }
        return TaskRef(id: id, title: title)
    }

    /// Move a step to just before `before` in its group. The target's position is read from the plan
    /// as it is now, because positions shift whenever the group changes.
    @discardableResult
    func place(stepId: String, before: TaskRef) async -> String? {
        guard let position = task(withId: before.id)?.position else { return nil }
        struct Body: Encodable { let position: Int }
        return await perform {
            let _: IDOnly = try await APIClient.shared.patch(
                "/api/v1/tasks/\(stepId)", body: Body(position: position)
            )
        }
    }

    /// "Remove from group": the step becomes an ordinary task again.
    @discardableResult
    func removeFromGroup(_ step: TimelineTask) async -> String? {
        await perform {
            let _: IDOnly = try await APIClient.shared.patch("/api/v1/tasks/\(step.id)", body: LeaveGroup())
        }
    }

    /// "Do this after…": `task` waits until `other` is done (TIME-322). A loop is refused by the server
    /// with a sentence that is shown as-is.
    @discardableResult
    func wait(_ task: TimelineTask, for other: TimelineTask) async -> String? {
        struct Body: Encodable { let prerequisite_task_id: String }
        return await perform {
            let _: IDOnly = try await APIClient.shared.post(
                "/api/v1/tasks/\(task.id)/prerequisites", body: Body(prerequisite_task_id: other.id)
            )
        }
    }

    /// "Don't wait": this task no longer waits for `ref`.
    @discardableResult
    func stopWaiting(task: TimelineTask, for ref: TaskRef) async -> String? {
        await perform {
            try await APIClient.shared.delete("/api/v1/tasks/\(task.id)/prerequisites/\(ref.id)")
        }
    }

    /// Delete a step from inside the detail sheet, reporting a refusal.
    @discardableResult
    func deleteStep(_ step: TimelineTask) async -> String? {
        let failure = await perform { try await APIClient.shared.delete("/api/v1/tasks/\(step.id)") }
        if failure == nil { TaskTimerStore.shared.stopIfTiming(taskId: step.id) }
        return failure
    }

    private func perform(_ operation: () async throws -> Void) async -> String? {
        do {
            try await operation()
            await load()
            return nil
        } catch {
            await load()
            return StepLabels.message(for: error)
        }
    }

    /// Delete a task that's completed or no longer viable (soft-delete on the backend).
    func deleteTask(taskId: String) async {
        try? await APIClient.shared.delete("/api/v1/tasks/\(taskId)")
        TaskTimerStore.shared.stopIfTiming(taskId: taskId)   // NowViewModel.removeTask already did
        await load()
    }

    /// Ask the engine for the earliest free block (avoiding calendar events + scheduled tasks). Falls
    /// back to "now + duration" if nothing fits today.
    func suggestedSlot(taskId: String, estimatedMinutes: Int?) async -> (start: Date, end: Date) {
        struct Resp: Decodable { let fits: Bool; let start: Date?; let end: Date? }
        let resp: Resp? = try? await APIClient.shared.get("/api/v1/tasks/\(taskId)/suggested-slot")
        if let resp, resp.fits, let s = resp.start, let e = resp.end {
            return (s, e)
        }
        let start = Date()
        return (start, start.addingTimeInterval(TimeInterval((estimatedMinutes ?? 30) * 60)))
    }

    /// Undo an auto-placed time — the task becomes untimed again.
    func unschedule(taskId: String) async {
        struct Empty: Encodable {}
        let _: IDOnly? = try? await APIClient.shared.post(
            "/api/v1/tasks/\(taskId)/unschedule", body: Empty()
        )
        await load()
    }

    func load() async {
        // Only the first load shows a spinner. A refresh keeps the plan on screen, so an open detail
        // sheet doesn't lose its task mid-edit (TIME-328).
        if case .loaded = uiState {} else { uiState = .loading }
        do {
            let today = DateFormatter.shortDate.string(from: Date())
            let items: [TimelineEntry] = try await APIClient.shared.get("/api/v1/timeline/today/plan?date=\(today)")
            recommendation = try? await APIClient.shared.get("/api/v1/now")
            uiState = .loaded(items)
            updateWidgetSnapshot(with: items)
        } catch {
            uiState = .error(error.localizedDescription)
        }
    }

    /// Updates only nextEvent (a task OR a calendar meeting, whichever is soonest), preserving whatever
    /// NowViewModel last wrote for usableMinutes/bestTask, then asks WidgetKit to refresh.
    private func updateWidgetSnapshot(with items: [TimelineEntry]) {
        let now = Date()
        let upcoming: [(title: String, start: Date, end: Date?)] = items
            .filter { $0.task?.status != "done" }   // done tasks skip; events have no status
            .compactMap { entry in
                guard let start = entry.start else { return nil }
                let end = entry.end ?? start
                guard end >= now else { return nil }
                return (entry.title, start, entry.end)
            }
        let next = upcoming.min { $0.start < $1.start }

        var snapshot = WidgetSnapshot.load() ?? .empty
        snapshot.nextEvent = next.map { WidgetSnapshot.Event(title: $0.title, start: $0.start, end: $0.end) }
        snapshot.updatedAt = Date()
        snapshot.save()
        WidgetCenter.shared.reloadAllTimelines()
    }

    func visualState(for task: TimelineTask) -> TimelineVisualState {
        let now = Date()
        if task.status == "done" { return .done }
        if let end = task.scheduledEnd, end < now { return .past }
        if let start = task.scheduledStart, let end = task.scheduledEnd,
           start <= now && now <= end { return .current }
        if let start = task.scheduledStart, start <= now && task.scheduledEnd == nil { return .current }
        return .future
    }
}

private struct IDOnly: Decodable { let id: String }

private struct StepsBody: Encodable {
    struct Step: Encodable {
        let title: String
        let estimated_minutes: Int?
    }
    let steps: [Step]
    /// Omitted when nil, which keeps the group's current ordering.
    let sequential: Bool?
}

/// `{"parent_task_id": null}`. The explicit null is what takes a step out of its group; a missing key
/// would leave it where it is, and synthesized encoding drops nil values.
private struct LeaveGroup: Encodable {
    enum CodingKeys: String, CodingKey { case parentTaskId = "parent_task_id" }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeNil(forKey: .parentTaskId)
    }
}

enum TimelineVisualState { case past, current, future, done }

private extension DateFormatter {
    static let shortDate: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()
}
