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
                // Hairline to define the white card against the soft canvas (mostly for light mode).
                RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                    .stroke(DesignTokens.Color.textSecondary.opacity(0.08), lineWidth: 0.5)
            )
            .shadow(
                color: DesignTokens.Shadow.card.color,
                radius: DesignTokens.Shadow.card.radius,
                x: DesignTokens.Shadow.card.x,
                y: DesignTokens.Shadow.card.y
            )
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
