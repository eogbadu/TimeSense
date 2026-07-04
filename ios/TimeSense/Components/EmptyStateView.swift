import SwiftUI

struct EmptyStateView: View {
    let icon: String
    let title: String
    let message: String
    var action: (() -> Void)? = nil
    var actionTitle: String = "Get Started"

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: icon)
                .font(.system(size: 44))
                .foregroundColor(DesignTokens.Color.accent.opacity(0.6))

            VStack(spacing: DesignTokens.Spacing.xs) {
                Text(title)
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                Text(message)
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .multilineTextAlignment(.center)
            }

            if let action {
                Button(actionTitle, action: action)
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundColor(DesignTokens.Color.accent)
            }
        }
        .padding(DesignTokens.Spacing.xl)
        .frame(maxWidth: .infinity)
    }
}
