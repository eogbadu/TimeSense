import SwiftUI

// MARK: – Card surface

struct CardModifier: ViewModifier {
    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
        content
            // Dark slate card (matches the reference) with a faint glass sheen + top-light edge,
            // and a subtle hairline — legible and consistent over the near-black background.
            .background(
                ZStack {
                    shape.fill(DesignTokens.Color.surface)
                    shape.fill(.ultraThinMaterial).opacity(0.10)
                    shape.fill(
                        LinearGradient(colors: [Color.white.opacity(0.04), .clear],
                                       startPoint: .top, endPoint: .bottom)
                    )
                }
            )
            .overlay(
                shape.stroke(
                    LinearGradient(colors: [Color.white.opacity(0.14), Color.white.opacity(0.04)],
                                   startPoint: .top, endPoint: .bottom),
                    lineWidth: 1
                )
            )
            .shadow(color: .black.opacity(0.30), radius: 16, x: 0, y: 8)
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
