import SwiftUI

// MARK: – Card surface

struct CardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                    .fill(DesignTokens.Color.surface)
            )
            .overlay(
                // Glass hairline — a subtle light edge that defines the card against the cosmic canvas.
                RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                    .stroke(DesignTokens.Color.hairline, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.22), radius: 16, x: 0, y: 8)
    }
}

extension View {
    func cardStyle() -> some View {
        modifier(CardModifier())
    }
}

// MARK: – Primary button

struct PrimaryButtonModifier: ViewModifier {
    var isDestructive: Bool = false

    func body(content: Content) -> some View {
        content
            .font(DesignTokens.Typography.headline)
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, DesignTokens.Spacing.md)
            .background(isDestructive ? DesignTokens.Color.destructive : DesignTokens.Color.accent)
            .cornerRadius(DesignTokens.Radius.pill)
    }
}

extension View {
    func primaryButtonStyle(isDestructive: Bool = false) -> some View {
        modifier(PrimaryButtonModifier(isDestructive: isDestructive))
    }
}

// MARK: – Section header

struct SectionHeaderModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(DesignTokens.Typography.caption)
            .foregroundColor(DesignTokens.Color.textSecondary)
            .textCase(.uppercase)
            .tracking(DesignTokens.Tracking.wide)
    }
}

extension View {
    func sectionHeaderStyle() -> some View {
        modifier(SectionHeaderModifier())
    }
}
