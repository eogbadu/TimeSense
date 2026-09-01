import Foundation

/// What the user is asked after finishing a task, when the assistant is still learning that kind of
/// work.
struct DurationPrompt: Identifiable, Equatable {
    let id: String   // the completed task's id
    let title: String
    /// What the assistant predicted — the sheet opens on this so the common case ("about right")
    /// is a single tap, and only a real disagreement costs any effort.
    let estimatedMinutes: Int?
    /// The library type this will teach. Shown so a wrong guess can be corrected, since a wrong
    /// type teaches the wrong bucket (TIME-286).
    let taskType: String?
    /// Minutes measured by the in-app timer, when the user used it. Pre-fills the sheet with a real
    /// figure rather than a guess.
    let measuredMinutes: Int?
    /// True when the user asked for this sheet rather than being asked. The server declined to
    /// prompt, so the sheet has to explain itself a little differently — and, crucially, must not
    /// let an unclassified task be saved against a type that teaches nothing.
    var isManual: Bool = false

    /// The server's catch-all type. An observation recorded against it is silently DISCARDED
    /// (`TaskDurationRepository.record_actual` returns early), so the sheet has to ask for a real
    /// type before a manual entry is worth saving.
    static let unclassifiedType = "general"
}

/// Guard against a timer left running overnight, or one stopped a few seconds after starting —
/// neither is a real observation, and feeding them in would poison the learned estimate.
func plausibleDurationMinutes(_ raw: Double) -> Int? {
    let rounded = Int(raw.rounded())
    return (1...480).contains(rounded) ? rounded : nil
}

/// Completing a task, and learning from it.
///
/// This lived inside `NowViewModel` until TIME-316, which meant the whole experience — ask how long
/// it took, keep a timed figure, stop the timer — was reachable from exactly one place: the Now
/// screen's recommended task. Completing anything from Today sent a bare status change, taught the
/// estimator nothing, and left a running timer going. The user's real need is the opposite case:
/// finishing something that was NOT the recommendation.
///
/// It is a protocol rather than a shared observable object on purpose. Now and Today are BOTH
/// mounted at all times (the tab pager keeps every screen alive), so a single shared
/// `@Published` prompt would have both screens trying to present the same sheet at once. Each view
/// model keeps its own prompt state and presents its own sheet; only the behaviour is shared.
// Wire payloads. At file scope because a protocol extension's methods are implicitly generic over
// `Self`, and Swift does not allow types nested inside a generic function.
private struct StatusUpdate: Encodable { let status: String }
private struct TaskIdResponse: Decodable { let id: String }
private struct DurationPromptResponse: Decodable { let ask: Bool; let task_type: String? }
private struct DurationFeedbackBody: Encodable { let actual_minutes: Int; let task_type: String? }
private struct DurationFeedbackResponse: Decodable { let estimated_minutes: Int }

@MainActor
protocol DurationPrompting: AnyObject {
    var durationPrompt: DurationPrompt? { get set }
}

extension DurationPrompting {
    /// Minutes measured by the running timer, if it is timing *this* task. Guarded, so an
    /// implausible figure is treated as no measurement at all rather than a bad one.
    func measuredMinutes(taskId: String) -> Int? {
        guard let seconds = TaskTimerStore.shared.elapsed(taskId: taskId) else { return nil }
        return plausibleDurationMinutes(seconds / 60)
    }

    /// Mark a task done, then learn from it. Callers reload afterwards themselves, because Now and
    /// Today reload differently.
    ///
    /// The measurement is read BEFORE the status change: the reload that follows can clear timer
    /// state, and the elapsed time is gone once that happens.
    func completeAndMaybeAskDuration(taskId: String, title: String,
                                     estimatedMinutes: Int?) async {
        let measured = measuredMinutes(taskId: taskId)
        let updated: TaskIdResponse? = try? await APIClient.shared.patch(
            "/api/v1/tasks/\(taskId)", body: StatusUpdate(status: "done")
        )
        guard updated != nil else { return }   // nothing was completed, so nothing to learn from
        await maybePromptDuration(taskId: taskId, title: title,
                                  estimatedMinutes: estimatedMinutes, measured: measured)
        TaskTimerStore.shared.stopIfTiming(taskId: taskId)
    }

    /// Ask only while the assistant is still learning this type — the server owns that decision, so
    /// the question fades away on its own instead of becoming a permanent tax on finishing things.
    func maybePromptDuration(taskId: String, title: String,
                             estimatedMinutes: Int?, measured: Int?) async {
        guard let resp: DurationPromptResponse = try? await APIClient.shared.get(
            "/api/v1/tasks/\(taskId)/duration-prompt"
        ) else { return }

        // A measured duration is worth recording even once the assistant has stopped asking about
        // this type — it's free, and more observations only sharpen the estimate.
        if let measured, !resp.ask {
            await submitDuration(taskId: taskId, minutes: measured)
            return
        }
        guard resp.ask else { return }
        durationPrompt = DurationPrompt(
            id: taskId, title: title, estimatedMinutes: estimatedMinutes,
            taskType: resp.task_type, measuredMinutes: measured
        )
    }

    /// Open the duration sheet because the USER asked to, not because the server did.
    ///
    /// `should_ask` deliberately goes quiet once a type is well learned, and never speaks at all for
    /// a task it could not classify — that gate is what keeps the question from becoming a tax on
    /// finishing things. But it also means a user who WANTS to record a real figure has nowhere to
    /// put it, which is what on-device testing of TIME-316 found: a plan full of completed tasks and
    /// no way to say how long any of them took.
    ///
    /// So the gate still owns whether we ASK; it does not own whether the user may ANSWER. The same
    /// endpoint is called purely for its resolved `task_type`, and `ask` is ignored.
    func promptDurationManually(taskId: String, title: String, estimatedMinutes: Int?) async {
        let resp: DurationPromptResponse? = try? await APIClient.shared.get(
            "/api/v1/tasks/\(taskId)/duration-prompt"
        )
        durationPrompt = DurationPrompt(
            id: taskId, title: title, estimatedMinutes: estimatedMinutes,
            taskType: resp?.task_type ?? DurationPrompt.unclassifiedType,
            measuredMinutes: measuredMinutes(taskId: taskId),
            isManual: true
        )
    }

    /// Record how long the task actually took → teaches the per-user estimate for its type.
    /// `taskType` carries a correction when the user says the detected type was wrong.
    func submitDuration(taskId: String, minutes: Int, taskType: String? = nil) async {
        let _: DurationFeedbackResponse? = try? await APIClient.shared.post(
            "/api/v1/tasks/\(taskId)/duration-feedback",
            body: DurationFeedbackBody(actual_minutes: minutes, task_type: taskType)
        )
        durationPrompt = nil
    }
}
