import SwiftUI

struct TodayView: View {
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                    DayProgressCard()
                    TaskListSection()
                }
                .padding(.horizontal, DesignTokens.Spacing.md)
                .padding(.top, DesignTokens.Spacing.sm)
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Today")
            .navigationBarTitleDisplayMode(.large)
        }
    }
}

private struct DayProgressCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text(Date(), style: .date)
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                Spacer()
                Text("0 of 0 done")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            ProgressView(value: 0.0)
                .tint(DesignTokens.Color.accent)
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}

private struct TaskListSection: View {
    var body: some View {
        EmptyStateView(
            icon: "calendar.badge.plus",
            title: "No tasks today",
            message: "Capture something to get started."
        )
    }
}
