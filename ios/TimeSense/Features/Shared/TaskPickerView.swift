import SwiftUI

/// Pick one of today's tasks, for "Do this after…" and "Make it a step of…" (TIME-328).
///
/// The caller decides which tasks are allowed (`StepLabels.waitCandidates` / `parentCandidates`), so a
/// choice the server would refuse is never on the list. This view only searches and reports the pick.
/// It is pushed inside a sheet's NavigationStack, so picking returns to that sheet.
struct TaskPickerView: View {
    let title: String
    /// One calm sentence above the list saying what picking does.
    let prompt: String
    let candidates: [TimelineTask]
    let onPick: (TimelineTask) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var query = ""

    private var matches: [TimelineTask] { StepLabels.search(candidates, for: query) }

    var body: some View {
        Group {
            if candidates.isEmpty {
                EmptyStateView(
                    icon: "tray",
                    title: "Nothing to choose yet",
                    message: "Tasks you haven't finished show up here."
                )
            } else {
                List {
                    Section {
                        ForEach(matches) { task in
                            Button {
                                UIImpactFeedbackGenerator(style: .light).impactOccurred()
                                onPick(task)
                                dismiss()
                            } label: {
                                row(task)
                            }
                            .buttonStyle(.plain)
                        }
                    } header: {
                        Text(prompt)
                            .textCase(nil)
                    }
                }
                .listStyle(.insetGrouped)
                .scrollContentBackground(.hidden)
                .searchable(text: $query, prompt: "Search tasks")
                .overlay {
                    if matches.isEmpty {
                        ContentUnavailableView.search(text: query)
                    }
                }
            }
        }
        .background(DesignTokens.Color.background)
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func row(_ task: TimelineTask) -> some View {
        let style = taskCategoryStyle(for: task.title)
        return HStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: task.isGroup ? "list.bullet" : style.icon)
                .foregroundColor(task.isGroup ? DesignTokens.Color.accent : style.color)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: 2) {
                Text(task.title)
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(2)
                if let detail = StepLabels.pickerDetail(for: task) {
                    Text(detail)
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 0)
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
    }
}
