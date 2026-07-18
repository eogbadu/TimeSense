import SwiftUI

// MARK: – Card surface

struct CardModifier: ViewModifier {
    @Environment(\.colorScheme) private var scheme

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
        let isDark = scheme == .dark
        content
            // Adaptive card: the surface token flips light/dark; the top-light sheen, hairline stroke,
            // and drop shadow are tuned per scheme (a light card needs a dark hairline + soft shadow).
            .background(
                ZStack {
                    shape.fill(DesignTokens.Color.surface)
                    shape.fill(.ultraThinMaterial).opacity(0.10)
                    shape.fill(
                        LinearGradient(colors: [Color.white.opacity(isDark ? 0.04 : 0), .clear],
                                       startPoint: .top, endPoint: .bottom)
                    )
                }
            )
            .overlay(
                shape.stroke(
                    isDark
                        ? LinearGradient(colors: [Color.white.opacity(0.14), Color.white.opacity(0.04)],
                                         startPoint: .top, endPoint: .bottom)
                        : LinearGradient(colors: [Color.black.opacity(0.08), Color.black.opacity(0.03)],
                                         startPoint: .top, endPoint: .bottom),
                    lineWidth: 1
                )
            )
            .shadow(color: .black.opacity(isDark ? 0.30 : 0.06), radius: isDark ? 16 : 10, x: 0, y: isDark ? 8 : 4)
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
