import SwiftUI

// "How long did that take?" — shared by every screen that can complete a task.
//
// It lived inside NowView.swift until TIME-316, which is why only the Now screen's recommended task
// could ever ask. Completing anything from Today taught the assistant nothing, even though this
// sheet was sitting right there, already built for exactly that. Moving it out is what lets Today
// use one copy rather than a second implementation drifting out of step.

/// The design goals here, in order:
///   1. Never become a chore. It opens on the assistant's own estimate (or the timed figure), so
///      "that was about right" is one tap, and Skip is always available.
///   2. Let a real number be given. A stepper reaches any value; the presets are shortcuts, not
///      the only options.
///   3. Let a wrong guess be corrected. A wrong type teaches the wrong bucket, so the detected type
///      is shown and can be changed.
struct DurationFeedbackSheet: View {
    let prompt: DurationPrompt
    let onSubmit: (Int, String?) -> Void
    let onSkip: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var minutes: Int
    @State private var correctedType: String?
    @State private var showTypePicker = false

    private static let presets = [5, 10, 15, 30, 45, 60, 90, 120]

    init(prompt: DurationPrompt, onSubmit: @escaping (Int, String?) -> Void,
         onSkip: @escaping () -> Void) {
        self.prompt = prompt
        self.onSubmit = onSubmit
        self.onSkip = onSkip
        // Open on the best figure available: what we timed, else what we predicted, else a neutral
        // starting point. Anchoring on our own estimate keeps the common case to a single tap.
        _minutes = State(initialValue: prompt.measuredMinutes ?? prompt.estimatedMinutes ?? 30)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    Text(prompt.title)
                        .font(DesignTokens.Typography.headline)
                        .foregroundColor(DesignTokens.Color.textPrimary)

                    if prompt.measuredMinutes != nil {
                        Label("Timed in the app — adjust if it's not right",
                              systemImage: "stopwatch")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                    }

                    // The value itself, big and directly adjustable.
                    HStack {
                        Stepper(value: $minutes, in: 1...480, step: 5) {
                            HStack(alignment: .firstTextBaseline, spacing: 4) {
                                Text("\(minutes)")
                                    .font(DesignTokens.Typography.title2)
                                    .foregroundColor(DesignTokens.Color.textPrimary)
                                    .monospacedDigit()
                                Text("min")
                                    .font(DesignTokens.Typography.callout)
                                    .foregroundColor(DesignTokens.Color.textSecondary)
                            }
                        }
                    }
                    .padding(DesignTokens.Spacing.lg)
                    .cardStyle()

                    // Shortcuts, not the only options — the stepper above reaches any value.
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                        Text("Quick pick")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                        LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 4),
                                  spacing: DesignTokens.Spacing.sm) {
                            ForEach(Self.presets, id: \.self) { value in
                                Button {
                                    minutes = value
                                } label: {
                                    Text(label(for: value))
                                        .font(DesignTokens.Typography.footnote)
                                        .frame(maxWidth: .infinity)
                                        .padding(.vertical, DesignTokens.Spacing.sm)
                                        .background(
                                            Capsule().fill(minutes == value
                                                           ? DesignTokens.Color.accent
                                                           : DesignTokens.Color.surface)
                                        )
                                        .foregroundColor(minutes == value
                                                         ? DesignTokens.Color.onHero
                                                         : DesignTokens.Color.textPrimary)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }

                    // A wrong type teaches the wrong bucket, so make it correctable here rather
                    // than hiding the assistant's guess (TIME-285/286).
                    if let detected = prompt.taskType {
                        Button {
                            showTypePicker = true
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Counted as")
                                        .font(DesignTokens.Typography.footnote)
                                        .foregroundColor(DesignTokens.Color.textSecondary)
                                    Text(friendlyType(correctedType ?? detected))
                                        .font(DesignTokens.Typography.callout)
                                        .foregroundColor(DesignTokens.Color.textPrimary)
                                }
                                Spacer()
                                Text("Change")
                                    .font(DesignTokens.Typography.footnote)
                                    .foregroundColor(DesignTokens.Color.accent)
                            }
                            .padding(DesignTokens.Spacing.lg)
                            .cardStyle()
                        }
                        .buttonStyle(.plain)
                    }

                    Text("This is how TimeSense learns your pace for this kind of task.")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("How long did that take?")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Skip") { onSkip(); dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { onSubmit(minutes, correctedType); dismiss() }
                        .fontWeight(.semibold)
                }
            }
            .sheet(isPresented: $showTypePicker) {
                TaskTypePickerSheet(selected: correctedType ?? prompt.taskType) { picked in
                    correctedType = picked
                    showTypePicker = false
                }
            }
        }
    }

    private func label(for value: Int) -> String {
        value < 60 ? "\(value)m" : (value % 60 == 0 ? "\(value / 60)h" : "\(value / 60)h\(value % 60)")
    }
}

/// Turns a library key ("appt_dentist") into something readable ("Dentist appointment").
/// The full catalogue lives on the server; the client only ever needs to render what it was given
/// and offer a short list of common corrections, so this stays a presentation concern.
func friendlyType(_ key: String) -> String {
    TaskTypeOption.all.first { $0.key == key }?.label
        ?? key.replacingOccurrences(of: "_", with: " ").capitalized
}

struct TaskTypeOption: Identifiable, Hashable {
    let key: String
    let label: String
    var id: String { key }

    /// A deliberately short list of the corrections people actually make. Offering all ~80 server
    /// types would turn a two-second correction into a search problem — and the server still
    /// accepts any valid key, so nothing is lost.
    static let all: [TaskTypeOption] = [
        .init(key: "meeting_generic", label: "Meeting"),
        .init(key: "call_generic", label: "Phone call"),
        .init(key: "email_reply", label: "Email"),
        .init(key: "message_send", label: "Message"),
        .init(key: "write_generic", label: "Writing"),
        .init(key: "code_feature", label: "Build a feature"),
        .init(key: "code_bugfix", label: "Fix a bug"),
        .init(key: "code_review", label: "Code review"),
        .init(key: "study_research", label: "Research"),
        .init(key: "read_book", label: "Reading"),
        .init(key: "plan_day", label: "Planning"),
        .init(key: "admin_generic", label: "Admin"),
        .init(key: "errand_generic", label: "Errand"),
        .init(key: "shop_generic", label: "Shopping"),
        .init(key: "chore_generic", label: "Household chore"),
        .init(key: "cook_meal", label: "Cooking"),
        .init(key: "exercise_gym", label: "Exercise"),
        .init(key: "social_meetup", label: "Seeing someone"),
        .init(key: "travel_generic", label: "Travel"),
        .init(key: "hobby_practice", label: "Practice / hobby"),
    ]
}

private struct TaskTypePickerSheet: View {
    let selected: String?
    let onPick: (String) -> Void

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List(TaskTypeOption.all) { option in
                Button {
                    onPick(option.key)
                    dismiss()
                } label: {
                    HStack {
                        Text(option.label)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        Spacer()
                        if option.key == selected {
                            Image(systemName: "checkmark")
                                .foregroundColor(DesignTokens.Color.accent)
                        }
                    }
                }
            }
            .navigationTitle("What kind of task?")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}