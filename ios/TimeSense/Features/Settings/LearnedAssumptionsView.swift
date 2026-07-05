import SwiftUI

private let routineOrder = ["sleep", "breakfast", "lunch", "dinner", "morning_hygiene", "evening_hygiene"]

private func routineLabel(_ routineType: String) -> String {
    switch routineType {
    case "sleep": return "Sleep"
    case "breakfast": return "Breakfast"
    case "lunch": return "Lunch"
    case "dinner": return "Dinner"
    case "morning_hygiene": return "Morning Routine"
    case "evening_hygiene": return "Evening Routine"
    default: return routineType.capitalized
    }
}

private func timeString(minuteOfDay minute: Int) -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "h:mm a"
    return formatter.string(from: date(fromMinuteOfDay: minute))
}

private func date(fromMinuteOfDay minute: Int) -> Date {
    var components = DateComponents()
    components.hour = minute / 60
    components.minute = minute % 60
    return Calendar.current.date(from: components) ?? Date()
}

private func minuteOfDay(from date: Date) -> Int {
    let components = Calendar.current.dateComponents([.hour, .minute], from: date)
    return (components.hour ?? 0) * 60 + (components.minute ?? 0)
}

struct LearnedAssumptionsView: View {
    @StateObject private var viewModel = LearnedAssumptionsViewModel()
    @State private var editingRoutine: RoutineAssumption?

    var body: some View {
        Group {
            switch viewModel.uiState {
            case .idle, .loading:
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
            case .error(let message):
                EmptyStateView(icon: "exclamationmark.circle", title: "Couldn't load", message: message)
            case .loaded(let routines):
                List(sorted(routines)) { routine in
                    Button {
                        editingRoutine = routine
                    } label: {
                        RoutineRow(routine: routine)
                    }
                    .buttonStyle(.plain)
                }
                .scrollContentBackground(.hidden)
            }
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Learned Assumptions")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .sheet(item: $editingRoutine) { routine in
            EditRoutineSheet(routine: routine) { startMinute, endMinute in
                await viewModel.update(
                    routineType: routine.routineType,
                    startMinute: startMinute,
                    endMinute: endMinute
                )
            }
        }
    }

    private func sorted(_ routines: [RoutineAssumption]) -> [RoutineAssumption] {
        routines.sorted {
            (routineOrder.firstIndex(of: $0.routineType) ?? routineOrder.count)
                < (routineOrder.firstIndex(of: $1.routineType) ?? routineOrder.count)
        }
    }
}

private struct RoutineRow: View {
    let routine: RoutineAssumption

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                HStack(spacing: DesignTokens.Spacing.xs) {
                    Text(routineLabel(routine.routineType))
                        .font(DesignTokens.Typography.body)
                        .foregroundColor(DesignTokens.Color.textPrimary)
                    if routine.isCustomized {
                        Text("Edited")
                            .font(DesignTokens.Typography.caption.weight(.semibold))
                            .foregroundColor(DesignTokens.Color.accent)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(DesignTokens.Color.accent.opacity(0.12))
                            .cornerRadius(DesignTokens.Radius.sm)
                    }
                }
                Text("\(timeString(minuteOfDay: routine.startMinute)) – \(timeString(minuteOfDay: routine.endMinute))")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
        }
        .contentShape(Rectangle())
    }
}

private struct EditRoutineSheet: View {
    let routine: RoutineAssumption
    let onSave: (Int, Int) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var startDate: Date
    @State private var endDate: Date
    @State private var isSaving = false

    init(routine: RoutineAssumption, onSave: @escaping (Int, Int) async -> Void) {
        self.routine = routine
        self.onSave = onSave
        _startDate = State(initialValue: date(fromMinuteOfDay: routine.startMinute))
        _endDate = State(initialValue: date(fromMinuteOfDay: routine.endMinute))
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    DatePicker("Starts", selection: $startDate, displayedComponents: .hourAndMinute)
                    DatePicker("Ends", selection: $endDate, displayedComponents: .hourAndMinute)
                } header: {
                    Text(routineLabel(routine.routineType))
                }
            }
            .navigationTitle("Edit Time")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        isSaving = true
                        Task {
                            await onSave(minuteOfDay(from: startDate), minuteOfDay(from: endDate))
                            isSaving = false
                            dismiss()
                        }
                    }
                    .disabled(isSaving)
                }
            }
        }
    }
}
