import SwiftUI

// Premium cosmic palette — matched to the reference: a near-black NEUTRAL navy base (not purple),
// dark slate cards, and muted blue→violet hero gradients.
enum Cosmic {
    // Single base navy — must equal the `Background` colour asset so flat and cosmic screens match.
    static let base    = Color(red: 0.031, green: 0.043, blue: 0.078)  // #080B14 near-black navy
    static let deep    = Color(red: 0.020, green: 0.027, blue: 0.055)  // #05070E darkest (bottom)
    static let surface = Color(red: 0.067, green: 0.078, blue: 0.122)  // #11141F dark slate card

    static let heroBlue   = Color(red: 0.227, green: 0.353, blue: 0.878) // #3A5AE0
    static let heroIndigo = Color(red: 0.369, green: 0.282, blue: 0.800) // #5E48CC
    static let heroViolet = Color(red: 0.541, green: 0.329, blue: 0.863) // #8A54DC

    static let glowBlue   = Color(red: 0.18, green: 0.39, blue: 1.00)
    static let glowViolet = Color(red: 0.48, green: 0.30, blue: 0.95)
}

/// The cosmic screen backdrop — a near-black neutral navy with only faint blue/violet corner glows
/// (matching the reference), not a heavy purple wash.
struct CosmicBackground: View {
    var body: some View {
        ZStack {
            LinearGradient(colors: [Cosmic.base, Cosmic.deep],
                           startPoint: .top, endPoint: .bottom)
            RadialGradient(colors: [Cosmic.glowBlue.opacity(0.10), .clear],
                           center: .topLeading, startRadius: 0, endRadius: 440)
            RadialGradient(colors: [Cosmic.glowViolet.opacity(0.10), .clear],
                           center: .topTrailing, startRadius: 0, endRadius: 440)
        }
        .ignoresSafeArea()
    }
}

/// The muted blue→indigo→violet hero gradient (primary recommendation cards).
/// `end` optionally warms the tail (energy green for health); nil keeps the pure blue→violet.
func heroGradient(end: Color? = nil) -> LinearGradient {
    LinearGradient(
        stops: [
            .init(color: Cosmic.heroBlue, location: 0.0),
            .init(color: Cosmic.heroIndigo, location: 0.55),
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
