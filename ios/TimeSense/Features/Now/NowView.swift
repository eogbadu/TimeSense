import SwiftUI

struct NowView: View {
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    ContextSummaryCard()
                    CurrentFocusCard()
                    UpNextSection()
                }
                .padding(.horizontal, DesignTokens.Spacing.md)
                .padding(.top, DesignTokens.Spacing.sm)
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Now")
            .navigationBarTitleDisplayMode(.large)
        }
    }
}

// MARK: – Subviews

private struct ContextSummaryCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Good morning")
                .font(DesignTokens.Typography.title2)
                .foregroundColor(DesignTokens.Color.textPrimary)
            Text("Here's what matters right now.")
                .font(DesignTokens.Typography.callout)
                .foregroundColor(DesignTokens.Color.textSecondary)
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}

private struct CurrentFocusCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Current Focus")
                .sectionHeaderStyle()
            HStack {
                RoundedRectangle(cornerRadius: 4)
                    .fill(DesignTokens.Color.accent)
                    .frame(width: 4)
                Text("No active focus block")
                    .font(DesignTokens.Typography.body)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }
}

private struct UpNextSection: View {
    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Up Next")
                .sectionHeaderStyle()
            EmptyStateView(
                icon: "sparkles",
                title: "Nothing scheduled",
                message: "Add tasks via Capture to see them here."
            )
        }
    }
}
