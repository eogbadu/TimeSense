import XCTest
@testable import TimeSense

/// TIME-327. A step on its own ("Get photos") didn't say what it was for, and a task waiting on
/// another looked exactly like one you could start. These pin how the plan's steps and waits are
/// decoded, worded and chosen.
final class StepGroupTests: XCTestCase {

    private func decode<T: Decodable>(_ json: String, as type: T.Type = T.self) throws -> T {
        try JSONDecoder().decode(T.self, from: Data(json.utf8))
    }

    private func task(_ id: String, _ title: String, status: String = "pending",
                      parent: String? = nil, extra: String = "") -> String {
        let parentFields = parent.map { #","parent_task_id":"p","parent_title":"\#($0)""# } ?? ""
        return #"{"id":"\#(id)","title":"\#(title)","status":"\#(status)","scheduled_start":null,"scheduled_end":null,"estimated_minutes":15,"priority":2,"auto_scheduled":false\#(parentFields)\#(extra)}"#
    }

    /// Renew passport → Get photos (done), Fill out the form, Mail it (after the form, and after stamps).
    private var group: String {
        let steps = [
            task("s1", "Get photos", status: "done", parent: "Renew passport",
                 extra: #","step_number":1,"parent_step_count":3,"blocked_by":[]"#),
            task("s2", "Fill out the form", parent: "Renew passport",
                 extra: #","step_number":2,"parent_step_count":3,"blocked_by":[{"id":"appt","title":"Book appointment"}]"#),
            task("s3", "Mail it", parent: "Renew passport",
                 extra: #","step_number":3,"parent_step_count":3,"blocked_by":[{"id":"s2","title":"Fill out the form"},{"id":"stamps","title":"Buy stamps"},{"id":"appt","title":"Book appointment"}]"#),
        ].joined(separator: ",")
        return task("p", "Renew passport",
                    extra: #","step_count":3,"open_step_count":2,"blocked_by":[{"id":"appt","title":"Book appointment"}],"steps":[\#(steps)]"#)
    }

    // MARK: - Decoding

    func testAGroupDecodesWithItsStepsInOrder() throws {
        let parent: TimelineTask = try decode(group)
        XCTAssertTrue(parent.isGroup)
        XCTAssertEqual(parent.groupSteps.map(\.title), ["Get photos", "Fill out the form", "Mail it"])
        XCTAssertEqual(parent.doneStepCount, 1)
        XCTAssertEqual(parent.openSteps.map(\.id), ["s2", "s3"])
        XCTAssertEqual(parent.groupSteps[2].parentTitle, "Renew passport")
    }

    func testAResponseFromBeforeStepsExistedStillDecodes() throws {
        let plain: TimelineTask = try decode(task("t", "Call the bank"))
        XCTAssertFalse(plain.isGroup)
        XCTAssertTrue(plain.waitsFor.isEmpty)
        XCTAssertFalse(plain.isWaiting)

        let now: NowTask = try decode(#"{"id":"t","title":"Call the bank","status":"pending","estimated_minutes":10,"priority":3,"due_at":null}"#)
        XCTAssertNil(now.eyebrow)
    }

    func testAFinishedTaskIsNeverShownAsWaiting() throws {
        let finished: TimelineTask = try decode(task("t", "Pay contractor", status: "done",
                                                     extra: #","blocked_by":[{"id":"i","title":"Get invoice"}]"#))
        XCTAssertFalse(finished.isWaiting)
    }

    // MARK: - Wording

    func testTheEyebrowNamesTheParentAndTheStep() throws {
        let step: NowTask = try decode(#"{"id":"s1","title":"Get photos","status":"pending","estimated_minutes":15,"priority":2,"due_at":null,"parent_title":"Renew passport","step_number":1,"parent_step_count":3}"#)
        XCTAssertEqual(step.eyebrow, "RENEW PASSPORT · STEP 1 OF 3")
        XCTAssertEqual(StepLabels.eyebrow(parentTitle: "Renew passport", stepNumber: nil, stepCount: nil),
                       "RENEW PASSPORT")
        XCTAssertNil(StepLabels.eyebrow(parentTitle: "  ", stepNumber: 1, stepCount: 3))
        XCTAssertEqual(StepLabels.spokenEyebrow(parentTitle: "Renew passport", stepNumber: 1, stepCount: 3),
                       "Step 1 of 3, part of Renew passport")
    }

    func testTheWaitingCaptionNamesWhatItWaitsFor() {
        let invoice = TaskRef(id: "i", title: "Get invoice")
        let quote = TaskRef(id: "q", title: "Get quote")
        XCTAssertEqual(StepLabels.waitingCaption([invoice]), "After: Get invoice")
        XCTAssertEqual(StepLabels.waitingCaption([invoice, quote]), "After: Get invoice + 1 more")
        XCTAssertNil(StepLabels.waitingCaption([]))
    }

    func testProgressAndTheFinishGroupQuestion() {
        XCTAssertEqual(StepLabels.progress(done: 1, total: 3), "1 of 3 steps")
        XCTAssertEqual(StepLabels.progress(done: 0, total: 1), "0 of 1 step")
        XCTAssertEqual(StepLabels.completeGroupPrompt(openSteps: 2), "Mark all 2 remaining steps done?")
        XCTAssertEqual(StepLabels.completeGroupPrompt(openSteps: 1), "Mark the last step done too?")
    }

    func testSiriSaysWhatAStepIsFor() {
        XCTAssertEqual(StepLabels.spoken(title: "Get photos", parentTitle: "Renew passport"),
                       "Get photos, for Renew passport")
        XCTAssertEqual(StepLabels.spoken(title: "Call the bank", parentTitle: nil), "Call the bank")
    }

    // MARK: - Choosing

    func testOnlyAWaitTheUserSetCanBeRemovedFromAStep() throws {
        let parent: TimelineTask = try decode(group)
        let mail = parent.groupSteps[2]
        // Fill out the form is the group's own order; Book appointment is inherited from the parent.
        XCTAssertEqual(StepLabels.removableWaits(for: mail, in: parent).map(\.id), ["stamps"])
    }

    func testTheSwapPickerOffersOpenStepsNotGroupsAndNothingWaiting() throws {
        let entries: [TimelineEntry] = try decode("""
        [
          {"kind":"task","id":"p","title":"Renew passport","start":null,"end":null,"location":null,"task":\(group)},
          {"kind":"task","id":"pay","title":"Pay contractor","start":null,"end":null,"location":null,
           "task":\(task("pay", "Pay contractor", extra: #","blocked_by":[{"id":"i","title":"Get invoice"}]"#))},
          {"kind":"task","id":"bank","title":"Call the bank","start":null,"end":null,"location":null,
           "task":\(task("bank", "Call the bank"))},
          {"kind":"event","id":"apple:1","title":"Team sync","start":null,"end":null,"location":null,"task":null}
        ]
        """)

        let offered = StepLabels.swapCandidates(from: entries, excluding: "bank")

        // Get photos is done, Fill out the form and Mail it are waiting, Pay contractor is waiting.
        XCTAssertEqual(offered.map(\.id), [])
        XCTAssertEqual(StepLabels.swapCandidates(from: entries, excluding: "none").map(\.id), ["bank"])
    }

    // MARK: - Pickers and refusals (TIME-328)

    /// Renew passport (with its steps), Pay contractor (waiting on an invoice not in the plan),
    /// Call the bank, and a finished task.
    private func plan() throws -> [TimelineEntry] {
        try decode("""
        [
          {"kind":"task","id":"p","title":"Renew passport","start":null,"end":null,"location":null,"task":\(group)},
          {"kind":"task","id":"pay","title":"Pay contractor","start":null,"end":null,"location":null,
           "task":\(task("pay", "Pay contractor", extra: #","blocked_by":[{"id":"i","title":"Get invoice"}]"#))},
          {"kind":"task","id":"bank","title":"Call the bank","start":null,"end":null,"location":null,
           "task":\(task("bank", "Call the bank"))},
          {"kind":"task","id":"old","title":"Old errand","start":null,"end":null,"location":null,
           "task":\(task("old", "Old errand", status: "done"))}
        ]
        """)
    }

    func testDoThisAfterOffersOpenTasksAndNeverALoopOrItsOwnGroup() throws {
        let entries = try plan()
        let bank = try XCTUnwrap(StepLabels.findTask("bank", in: entries))
        XCTAssertEqual(StepLabels.waitCandidates(for: bank, in: entries).map(\.id), ["p", "s2", "s3", "pay"])

        // Mail it already waits for the form, and can't wait for its own group or a finished step.
        let mail = try XCTUnwrap(StepLabels.findTask("s3", in: entries))
        XCTAssertEqual(StepLabels.waitCandidates(for: mail, in: entries).map(\.id), ["pay", "bank"])

        // The form is waited on by Mail it, so offering Mail it would make the two wait on each other.
        let form = try XCTUnwrap(StepLabels.findTask("s2", in: entries))
        XCTAssertFalse(StepLabels.waitCandidates(for: form, in: entries).map(\.id).contains("s3"))
    }

    func testMakeItAStepOfOffersOnlyTasksThatCanHoldSteps() throws {
        let entries = try plan()
        let bank = try XCTUnwrap(StepLabels.findTask("bank", in: entries))
        XCTAssertEqual(StepLabels.parentCandidates(for: bank, in: entries).map(\.id), ["p", "pay"])

        let passport = try XCTUnwrap(StepLabels.findTask("p", in: entries))
        XCTAssertTrue(StepLabels.parentCandidates(for: passport, in: entries).isEmpty,
                      "a task with steps can't become a step")

        let form = try XCTUnwrap(StepLabels.findTask("s2", in: entries))
        XCTAssertEqual(StepLabels.parentCandidates(for: form, in: entries).map(\.id), ["pay", "bank"])
    }

    func testSearchMatchesTheTitleOrTheGroup() throws {
        let all = StepLabels.allTasks(in: try plan())
        XCTAssertEqual(StepLabels.search(all, for: "FORM").map(\.id), ["s2"])
        XCTAssertEqual(StepLabels.search(all, for: "passport").map(\.id), ["p", "s1", "s2", "s3"])
        XCTAssertEqual(StepLabels.search(all, for: "  ").count, all.count)
        XCTAssertEqual(StepLabels.pickerDetail(for: all[0]), "1 of 3 steps")
        XCTAssertEqual(StepLabels.pickerDetail(for: all[2]), "Part of Renew passport")
    }

    func testARefusalIsShownInTheServersOwnWords() {
        let loop = APIError.serverError(409, Data(#"{"detail":"That would make these tasks wait on each other."}"#.utf8))
        XCTAssertEqual(StepLabels.message(for: loop), "That would make these tasks wait on each other.")

        let full = APIError.validationError(Data(#"{"detail":"A task can have at most 12 steps."}"#.utf8))
        XCTAssertEqual(StepLabels.message(for: full), "A task can have at most 12 steps.")

        let schema = APIError.validationError(Data(#"{"detail":[{"loc":["body"],"msg":"field required"}]}"#.utf8))
        XCTAssertEqual(StepLabels.message(for: schema), "That didn't work. Please try again.")
        XCTAssertEqual(StepLabels.message(for: APIError.unauthorized), "That didn't work. Please try again.")
    }

    // MARK: - Capture (TIME-329)

    private func captured(_ extra: String) -> String {
        #"{"id":"c","title":"Get photos","status":"pending","priority":3,"estimated_minutes":15,"scheduled_start":null,"scheduled_end":null,"due_at":null,"auto_scheduled":false,"source":"capture"\#(extra)}"#
    }

    func testACaptureSaysWhereItLanded() throws {
        let joined: CapturedTask = try decode(captured(#","parent_task_id":"p","parent_title":"Renew passport","steps":[],"suggested_parent":null"#))
        XCTAssertEqual(joined.parentTitle, "Renew passport")
        XCTAssertTrue(joined.capturedSteps.isEmpty)
        XCTAssertNil(joined.suggestedParent)

        let group: CapturedTask = try decode(captured(#","parent_task_id":null,"steps":[{"id":"s1","title":"Get photos","estimated_minutes":15,"blocked_by":[]},{"id":"s2","title":"Mail it","estimated_minutes":null,"blocked_by":[{"id":"s1","title":"Get photos"}]}]"#))
        XCTAssertEqual(group.capturedSteps.map(\.title), ["Get photos", "Mail it"])
        XCTAssertEqual(group.capturedSteps[1].blockedBy, [TaskRef(id: "s1", title: "Get photos")])

        let suggested: CapturedTask = try decode(captured(#","suggested_parent":{"id":"p","title":"Renew passport"}"#))
        XCTAssertEqual(suggested.suggestedParent, TaskRef(id: "p", title: "Renew passport"))
    }

    func testACaptureFromBeforeGroupsExistedStillDecodes() throws {
        let old: CapturedTask = try decode(captured(""))
        XCTAssertNil(old.parentTitle)
        XCTAssertTrue(old.capturedSteps.isEmpty)
        XCTAssertNil(old.suggestedParent)
    }

    func testPartOfOffersTodaysOpenTasksThatArentSteps() throws {
        XCTAssertEqual(StepLabels.captureParentCandidates(in: try plan()).map(\.id), ["p", "pay", "bank"])
    }
}
