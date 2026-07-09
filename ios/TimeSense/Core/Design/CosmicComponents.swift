import SwiftUI

/// The cosmic screen backdrop — near-black navy with soft blue/violet auras top-corners, echoing the
/// app icon. Use behind scroll content: `.background(CosmicBackground())`.
struct CosmicBackground: View {
    var body: some View {
        ZStack {
            DesignTokens.Color.background
            RadialGradient(
                colors: [DesignTokens.Color.accent.opacity(0.20), .clear],
                center: .topTrailing, startRadius: 0, endRadius: 460
            )
            RadialGradient(
                colors: [DesignTokens.Color.accentBlue.opacity(0.16), .clear],
                center: .topLeading, startRadius: 0, endRadius: 420
            )
        }
        .ignoresSafeArea()
    }
}

/// A translucent white pill used for the signal chips on a gradient hero card.
struct HeroPill: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: icon).font(.caption2.weight(.semibold))
            Text(text).font(DesignTokens.Typography.caption.weight(.medium))
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(Capsule().fill(Color.white.opacity(0.16)))
        .overlay(Capsule().stroke(Color.white.opacity(0.18), lineWidth: 1))
    }
}

/// The signature blue→violet hero gradient, with the warm end swappable per recommendation domain.
func heroGradient(end: Color) -> LinearGradient {
    LinearGradient(
        colors: [DesignTokens.Color.accentBlue, end],
        startPoint: .topLeading, endPoint: .bottomTrailing
    )
}

/// A large glowing line-art style symbol for the top-right of a hero card.
struct HeroGlyph: View {
    let systemName: String

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: 40, weight: .regular))
            .foregroundStyle(.white)
            .shadow(color: .white.opacity(0.55), radius: 12)
            .shadow(color: DesignTokens.Color.accentBlue.opacity(0.5), radius: 18)
    }
}
