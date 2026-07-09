import SwiftUI

// MARK: – Card surface

struct CardModifier: ViewModifier {
    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
        content
            // Glassmorphism: frosted blur of the atmospheric background, tinted with a translucent
            // navy so content stays legible, then a soft top-light gradient for the "glass" edge.
            .background(
                ZStack {
                    shape.fill(.ultraThinMaterial)
                    shape.fill(DesignTokens.Color.surface.opacity(0.45))
                    shape.fill(
                        LinearGradient(colors: [Color.white.opacity(0.05), .clear],
                                       startPoint: .top, endPoint: .bottom)
                    )
                }
            )
            .overlay(
                shape.stroke(
                    LinearGradient(colors: [Color.white.opacity(0.22), Color.white.opacity(0.05)],
                                   startPoint: .top, endPoint: .bottom),
                    lineWidth: 1
                )
            )
            .shadow(color: .black.opacity(0.30), radius: 18, x: 0, y: 10)
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
