import SwiftUI

/// One task on its own (TIME-328): its steps, which task it is part of, and what it waits for.
///
/// This is the only place a task is shaped by hand, and it stays short on purpose. Most steps come from
/// Capture or "Break this down", and nothing here asks the user to organize their day. Every change
/// reloads the plan, and a refusal from the server is shown inline in the server's own words.
struct TaskDetailSheet: View {
    @ObservedObject var viewModel: TodayViewModel
    let taskId: String

    @Environment(\.dismiss) private var dismiss
    @State private var newStep = ""
    @State private var failure: String?
    @State private var busy = false
    @State private var suggestions: StepSuggestions?
    @State private var keptSuggestions: Set<String> = []
    @State private var loadingSuggestions = false
    /// "Before Fill out the form?", offered after the task joins an ordered group.
    @State private var placeOffer: PlaceOffer?

    private struct PlaceOffer: Equatable {
        let stepId: String
        let before: TaskRef
    }

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.uiState {
                case .idle, .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                case .error(let message):
                    EmptyStateView(icon: "exclamationmark.circle", title: "Couldn't load this task",
                                   message: message)
                case .loaded:
                    if let task = viewModel.task(withId: taskId) {
                        content(task)
                    } else {
                        EmptyStateView(icon: "checkmark.circle", title: "Not in today's plan",
                                       message: "It may have been finished or removed.")
                    }
                }
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }

    private func content(_ task: TimelineTask) -> some View {
        let group = viewModel.group(containing: task)
        return List {
            headerSection(task)
            if let failure {
                Section {
                    Label(failure, systemImage: "exclamationmark.circle")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.destructive)
                }
            }
            if let offer = placeOffer {
                placeSection(offer)
            }
            partOfSection(task)
            if task.parentTaskId == nil {
                stepsSection(task)
                if StepLabels.isOpen(task) { breakdownSection(task) }
            }
            waitsSection(task, group: group)
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .disabled(busy)
        .animation(.easeInOut(duration: 0.2), value: placeOffer)
    }

    // MARK: - Sections

    private func headerSection(_ task: TimelineTask) -> some View {
        Section {
            VStack(alignment: .leading, spacing: 6) {
                if let eyebrow = StepLabels.eyebrow(parentTitle: task.parentTitle, stepNumber: task.stepNumber,
                                                    stepCount: task.parentStepCount) {
                    Text(eyebrow)
                        .font(DesignTokens.Typography.caption.weight(.semibold))
                        .tracking(0.6)
                        .foregroundColor(DesignTokens.Color.accent)
                }
                Text(task.title)
                    .font(DesignTokens.Typography.title2.weight(.bold))
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .strikethrough(task.status == "done")
                Text(subtitle(task))
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            .padding(.vertical, 4)
        }
    }

    private func placeSection(_ offer: PlaceOffer) -> some View {
        Section {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Label("Before “\(offer.before.title)”?", systemImage: "sparkles")
                    .font(DesignTokens.Typography.callout.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.textPrimary)
                HStack(spacing: DesignTokens.Spacing.sm) {
                    Button("Yes") {
                        placeOffer = nil
                        run { await viewModel.place(stepId: offer.stepId, before: offer.before) }
                    }
                    .buttonStyle(.borderedProminent)
                    Button("No particular order") { placeOffer = nil }
                        .buttonStyle(.bordered)
                }
            }
            .padding(.vertical, 4)
        }
    }

    @ViewBuilder
    private func partOfSection(_ task: TimelineTask) -> some View {
        if let parentTitle = task.parentTitle {
            Section("Part of") {
                HStack {
                    Label(parentTitle, systemImage: "list.bullet")
                        .foregroundColor(DesignTokens.Color.textPrimary)
                    Spacer()
                    if StepLabels.isOpen(task) {
                        Button("Remove") { run { await viewModel.removeFromGroup(task) } }
                            .buttonStyle(.borderless)
                    }
                }
            }
        } else if !task.isGroup && StepLabels.isOpen(task) {
            Section {
                NavigationLink {
                    TaskPickerView(
                        title: "Make it a step of…",
                        prompt: "“\(task.title)” joins the task you pick.",
                        candidates: StepLabels.parentCandidates(for: task, in: viewModel.entries)
                    ) { parent in
                        run(
                            { await viewModel.makeStep(task, of: parent) },
                            then: { await offerPlace(stepId: task.id, parentId: parent.id) }
                        )
                    }
                } label: {
                    Label("Make it a step of…", systemImage: "arrow.down.right.square")
                }
            }
        }
    }

    private func stepsSection(_ task: TimelineTask) -> some View {
        Section {
            ForEach(task.groupSteps) { step in
                stepRow(step)
                    .swipeActions {
                        Button(role: .destructive) {
                            run { await viewModel.deleteStep(step) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    }
            }
            if StepLabels.isOpen(task) {
                HStack(spacing: DesignTokens.Spacing.sm) {
                    Image(systemName: "plus.circle.fill")
                        .foregroundColor(DesignTokens.Color.accent)
                    TextField("Add a step", text: $newStep)
                        .submitLabel(.done)
                        .onSubmit {
                            let title = newStep
                            newStep = ""
                            run { await viewModel.addStep(to: task, title: title) }
                        }
                }
            }
        } header: {
            Text(task.isGroup
                 ? StepLabels.progress(done: task.doneStepCount, total: task.groupSteps.count)
                 : "Steps")
        }
    }

    private func stepRow(_ step: TimelineTask) -> some View {
        let done = step.status == "done"
        return HStack(spacing: DesignTokens.Spacing.sm) {
            Image(systemName: done ? "checkmark.circle.fill" : "circle")
                .foregroundColor(done ? .green : DesignTokens.Color.textSecondary)
            VStack(alignment: .leading, spacing: 2) {
                Text(step.title)
                    .foregroundColor(done ? DesignTokens.Color.textSecondary : DesignTokens.Color.textPrimary)
                    .strikethrough(done)
                if !done, let caption = StepLabels.waitingCaption(step.waitsFor) {
                    Label(caption, systemImage: "hourglass")
                        .font(DesignTokens.Typography.caption)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            }
        }
        .opacity(step.isWaiting ? 0.55 : 1)
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder
    private func breakdownSection(_ task: TimelineTask) -> some View {
        Section {
            if loadingSuggestions {
                HStack(spacing: DesignTokens.Spacing.sm) {
                    ProgressView()
                    Text("Thinking of steps…")
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            } else if let suggestions {
                if suggestions.available && !suggestions.steps.isEmpty {
                    ForEach(suggestions.steps, id: \.self) { draft in
                        Toggle(isOn: keepBinding(draft.title)) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(draft.title)
                                if let minutes = draft.estimatedMinutes {
                                    Text("~\(minutes) min")
                                        .font(DesignTokens.Typography.caption)
                                        .foregroundColor(DesignTokens.Color.textSecondary)
                                }
                            }
                        }
                    }
                    let kept = suggestions.steps.filter { keptSuggestions.contains($0.title) }
                    Button {
                        run(
                            { await viewModel.addSteps(to: task, drafts: kept, sequential: suggestions.sequential) },
                            then: { self.suggestions = nil }
                        )
                    } label: {
                        Text(kept.count == 1 ? "Add 1 step" : "Add \(kept.count) steps")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(kept.isEmpty)
                } else {
                    Text(suggestions.available
                         ? "This already looks like a single step."
                         : "Couldn't suggest steps. Add your own above.")
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            } else {
                Button {
                    loadSuggestions(for: task)
                } label: {
                    Label("Break this down", systemImage: "sparkles")
                }
            }
        } footer: {
            if suggestions == nil && !loadingSuggestions {
                Text("TimeSense suggests steps. Nothing is added until you choose.")
            }
        }
    }

    @ViewBuilder
    private func waitsSection(_ task: TimelineTask, group: TimelineTask?) -> some View {
        let removable = group.map { StepLabels.removableWaits(for: task, in: $0) } ?? task.waitsFor
        if StepLabels.isOpen(task) || !task.waitsFor.isEmpty {
            Section {
                ForEach(task.waitsFor) { ref in
                    HStack {
                        Label(ref.title, systemImage: "hourglass")
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        Spacer()
                        if removable.contains(ref) {
                            Button("Don't wait") { run { await viewModel.stopWaiting(task: task, for: ref) } }
                                .buttonStyle(.borderless)
                        } else {
                            Text(waitOrigin(ref, group: group))
                                .font(DesignTokens.Typography.caption)
                                .foregroundColor(DesignTokens.Color.textSecondary)
                        }
                    }
                }
                if StepLabels.isOpen(task) {
                    NavigationLink {
                        TaskPickerView(
                            title: "Do this after…",
                            prompt: "“\(task.title)” waits until the task you pick is done.",
                            candidates: StepLabels.waitCandidates(for: task, in: viewModel.entries)
                        ) { other in
                            run { await viewModel.wait(task, for: other) }
                        }
                    } label: {
                        Label("Do this after…", systemImage: "arrow.turn.down.right")
                    }
                }
            } header: {
                Text("Waits for")
            } footer: {
                if task.waitsFor.isEmpty {
                    Text("Nothing. TimeSense can suggest this whenever it fits.")
                }
            }
        }
    }

    // MARK: - Helpers

    /// Why a wait on a step can't be removed here: it is the group's order, or it comes from the group.
    private func waitOrigin(_ ref: TaskRef, group: TimelineTask?) -> String {
        guard let group else { return "" }
        return group.groupSteps.contains { $0.id == ref.id } ? "Step order" : "Via \(group.title)"
    }

    private func subtitle(_ task: TimelineTask) -> String {
        if task.status == "done" { return "Done" }
        let minutes = task.estimatedMinutes.map { "\($0) min" }
        guard let start = task.scheduledStart else {
            return ["Anytime", minutes].compactMap { $0 }.joined(separator: "  ·  ")
        }
        return [start.formatted(date: .omitted, time: .shortened), minutes]
            .compactMap { $0 }
            .joined(separator: "  ·  ")
    }

    private func keepBinding(_ title: String) -> Binding<Bool> {
        Binding(
            get: { keptSuggestions.contains(title) },
            set: { keep in
                if keep { keptSuggestions.insert(title) } else { keptSuggestions.remove(title) }
            }
        )
    }

    private func loadSuggestions(for task: TimelineTask) {
        loadingSuggestions = true
        failure = nil
        Task {
            let result = await viewModel.breakdown(task)
            suggestions = result ?? StepSuggestions(available: false, steps: [], sequential: false)
            keptSuggestions = Set(result?.steps.map(\.title) ?? [])
            loadingSuggestions = false
        }
    }

    private func offerPlace(stepId: String, parentId: String) async {
        guard let before = await viewModel.suggestedPlace(for: stepId, in: parentId) else { return }
        placeOffer = PlaceOffer(stepId: stepId, before: before)
    }

    /// Run a change, show its refusal if there is one, and only then run `then`.
    private func run(_ action: @escaping () async -> String?, then after: (() async -> Void)? = nil) {
        busy = true
        failure = nil
        Task {
            let refusal = await action()
            failure = refusal
            if refusal == nil {
                UIImpactFeedbackGenerator(style: .light).impactOccurred()
                await after?()
            }
            busy = false
        }
    }
}

/// Opens a task's details from outside Today, such as the step label on Now, with its own copy of
/// today's plan.
struct TaskDetailHost: View {
    let taskId: String
    var onClose: () -> Void = {}

    @StateObject private var viewModel = TodayViewModel()

    var body: some View {
        TaskDetailSheet(viewModel: viewModel, taskId: taskId)
            .task { await viewModel.load() }
            .onDisappear(perform: onClose)
    }
}
