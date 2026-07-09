import SwiftUI

// Premium cosmic palette (muted, elegant — not harsh/saturated).
enum Cosmic {
    static let bgNear   = Color(red: 0.039, green: 0.043, blue: 0.078)  // #0A0B14 near-black navy
    static let bgNavy    = Color(red: 0.043, green: 0.063, blue: 0.145) // #0B1025 deep navy
    static let bgIndigo  = Color(red: 0.078, green: 0.043, blue: 0.157) // #140B28 midnight indigo

    static let heroBlue   = Color(red: 0.239, green: 0.400, blue: 0.945) // #3D66F1
    static let heroIndigo = Color(red: 0.416, green: 0.337, blue: 0.902) // #6A56E6
    static let heroViolet = Color(red: 0.600, green: 0.361, blue: 0.949) // #995CF2

    static let glowBlue   = Color(red: 0.30, green: 0.55, blue: 1.00)
    static let glowViolet = Color(red: 0.62, green: 0.40, blue: 1.00)
}

/// The cosmic screen backdrop — deep navy→indigo→violet with soft blue/violet glows, echoing the icon.
struct CosmicBackground: View {
    var body: some View {
        ZStack {
            LinearGradient(colors: [Cosmic.bgNear, Cosmic.bgNavy, Cosmic.bgIndigo],
                           startPoint: .top, endPoint: .bottom)
            RadialGradient(colors: [Cosmic.glowViolet.opacity(0.22), .clear],
                           center: .topTrailing, startRadius: 0, endRadius: 520)
            RadialGradient(colors: [Cosmic.glowBlue.opacity(0.18), .clear],
                           center: .topLeading, startRadius: 0, endRadius: 460)
            RadialGradient(colors: [Cosmic.heroIndigo.opacity(0.14), .clear],
                           center: .bottom, startRadius: 0, endRadius: 520)
        }
        .ignoresSafeArea()
    }
}

/// The signature soft blue→indigo→violet hero gradient (primary recommendation cards).
/// `end` optionally warms the tail (e.g. energy green for health); nil keeps the pure blue→violet.
func heroGradient(end: Color? = nil) -> LinearGradient {
    LinearGradient(
        stops: [
            .init(color: Cosmic.heroBlue, location: 0.0),
            .init(color: Cosmic.heroIndigo, location: 0.5),
            .init(color: end ?? Cosmic.heroViolet, location: 1.0),
        ],
        startPoint: .topLeading, endPoint: .bottomTrailing
    )
}

/// Neon edge-light stroke for primary cards (bright at top, fading down).
func neonEdge() -> LinearGradient {
    LinearGradient(colors: [.white.opacity(0.35), .white.opacity(0.06), Cosmic.glowViolet.opacity(0.20)],
                   startPoint: .top, endPoint: .bottom)
}

/// A translucent glass pill for the signal chips on a gradient hero card.
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
        .background(.ultraThinMaterial.opacity(0.5), in: Capsule())
        .background(Capsule().fill(Color.white.opacity(0.14)))
        .overlay(Capsule().stroke(Color.white.opacity(0.22), lineWidth: 1))
    }
}

/// A large glowing line-art style symbol for the top-right of a hero card.
struct HeroGlyph: View {
    let systemName: String

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: 40, weight: .regular))
            .foregroundStyle(.white)
            .shadow(color: .white.opacity(0.6), radius: 10)
            .shadow(color: Cosmic.glowBlue.opacity(0.6), radius: 20)
    }
}

/// Frosted-glass chrome for the primary recommendation card: neon edge + soft violet glow.
struct HeroCardChrome: ViewModifier {
    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
        content
            .clipShape(shape)
            .overlay(shape.stroke(neonEdge(), lineWidth: 1))
            .shadow(color: Cosmic.glowViolet.opacity(0.35), radius: 28, x: 0, y: 12)
            .shadow(color: Cosmic.glowBlue.opacity(0.20), radius: 16, x: 0, y: 4)
    }
}

extension View {
    func heroCardChrome() -> some View { modifier(HeroCardChrome()) }
}
