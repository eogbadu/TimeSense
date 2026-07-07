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

private func routineStyle(_ routineType: String) -> (icon: String, color: Color) {
    switch routineType {
    case "sleep":            return ("moon.fill", DesignTokens.Color.accent)
    case "breakfast":        return ("cup.and.saucer.fill", .orange)
    case "lunch":            return ("fork.knife", .green)
    case "dinner":           return ("fork.knife", .green)
    case "morning_hygiene":  return ("sun.max.fill", .yellow)
    case "evening_hygiene":  return ("moon.stars.fill", DesignTokens.Color.accent)
    default:                 return ("clock.fill", DesignTokens.Color.accent)
    }
}

private func confidenceLine(_ routine: RoutineAssumption) -> String {
    routine.isCustomized ? "High confidence  ·  Set by you" : "Medium confidence  ·  Default pattern"
}

struct LearnedAssumptionsView: View {
    @StateObject private var viewModel = LearnedAssumptionsViewModel()
    @State private var editingRoutine: RoutineAssumption?
    @State private var showAddComingSoon = false

    var body: some View {
        Group {
            switch viewModel.uiState {
            case .idle, .loading:
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
            case .error(let message):
                EmptyStateView(icon: "exclamationmark.circle", title: "Couldn't load", message: message)
            case .loaded(let routines):
                loaded(sorted(routines))
            }
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Learned Patterns")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .sheet(item: $editingRoutine) { routine in
            EditRoutineSheet(routine: routine) { startMinute, endMinute in
                await viewModel.update(routineType: routine.routineType, startMinute: startMinute, endMinute: endMinute)
            }
        }
        .alert("Manual patterns coming soon", isPresented: $showAddComingSoon) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("For now, TimeSense learns your patterns automatically — tap any to fine-tune it.")
        }
    }

    private func loaded(_ routines: [RoutineAssumption]) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                Text("TimeSense learns from your behavior to make smarter recommendations. You can edit or delete any pattern.")
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(DesignTokens.Spacing.lg)
                    .background(
                        RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                            .fill(DesignTokens.Color.accent.opacity(0.10))
                    )

                VStack(spacing: 0) {
                    ForEach(Array(routines.enumerated()), id: \.element.id) { idx, routine in
                        Button { editingRoutine = routine } label: { PatternRow(routine: routine) }
                            .buttonStyle(.plain)
                        if idx < routines.count - 1 { Divider().padding(.leading, 62) }
                    }
                }
                .cardStyle()

                Button { showAddComingSoon = true } label: {
                    Label("Add manual pattern", systemImage: "plus")
                        .font(DesignTokens.Typography.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, DesignTokens.Spacing.md)
                        .background(Capsule().fill(DesignTokens.Color.accent))
                }
                .padding(.top, DesignTokens.Spacing.sm)
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
    }

    private func sorted(_ routines: [RoutineAssumption]) -> [RoutineAssumption] {
        routines.sorted {
            (routineOrder.firstIndex(of: $0.routineType) ?? routineOrder.count)
                < (routineOrder.firstIndex(of: $1.routineType) ?? routineOrder.count)
        }
    }
}

private struct PatternRow: View {
    let routine: RoutineAssumption

    var body: some View {
        let style = routineStyle(routine.routineType)
        HStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: style.icon)
                .font(.title2)
                .foregroundColor(style.color)
                .frame(width: 40, height: 40)
            VStack(alignment: .leading, spacing: 2) {
                Text(routineLabel(routine.routineType))
                    .font(DesignTokens.Typography.callout.weight(.semibold))
                    .foregroundColor(DesignTokens.Color.textPrimary)
                Text("\(timeString(minuteOfDay: routine.startMinute)) – \(timeString(minuteOfDay: routine.endMinute))")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                Text(confidenceLine(routine))
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            Spacer(minLength: 0)
            Image(systemName: "chevron.right")
                .font(.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
        }
        .padding(DesignTokens.Spacing.md)
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
