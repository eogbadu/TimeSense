import SwiftUI

// Premium cosmic palette — matched to the reference: a near-black NEUTRAL navy base, dark slate
// cards, and recommendation cards that are DARK with a domain-coloured glow (not a bright gradient).
enum Cosmic {
    // Single base navy — must equal the `Background` colour asset so flat and cosmic screens match.
    static let base    = Color(red: 0.031, green: 0.043, blue: 0.078)  // #080B14 near-black navy
    static let deep    = Color(red: 0.020, green: 0.027, blue: 0.055)  // #05070E darkest (bottom)
    static let surface = Color(red: 0.067, green: 0.078, blue: 0.122)  // #11141F dark slate card

    // Dark navy base for the hero card (blooms into the domain colour top-right).
    static let heroBaseTop = Color(red: 0.055, green: 0.086, blue: 0.165) // #0E162A
    static let heroBaseBot = Color(red: 0.035, green: 0.051, blue: 0.106) // #090D1B

    // Semantic domain accents — the multiple colours the reference uses across the home screen.
    static let green  = Color(red: 0.208, green: 0.839, blue: 0.627) // #35D6A0 energy/health
    static let blue   = Color(red: 0.239, green: 0.545, blue: 1.000) // #3D8BFF focus/calendar
    static let cyan   = Color(red: 0.141, green: 0.780, blue: 0.867) // #24C7DD errand/nearby
    static let violet = Color(red: 0.604, green: 0.420, blue: 1.000) // #9A6BFF meeting/appointment/tasks
    static let amber  = Color(red: 1.000, green: 0.706, blue: 0.302) // #FFB44D warnings/deadlines

    static let glowBlue   = Color(red: 0.18, green: 0.39, blue: 1.00)
    static let glowViolet = Color(red: 0.48, green: 0.30, blue: 0.95)
}

/// Recommendation category → its accent colour (drives the hero glow, icon, and pills).
func heroAccent(_ descriptor: String) -> Color {
    switch descriptor {
    case "Health break":         return Cosmic.green
    case "Errand", "Chore":      return Cosmic.cyan
    case "Appointment", "Meeting": return Cosmic.violet
    case "Focus task":           return Cosmic.blue
    case "Quick task":           return Cosmic.green
    default:                     return Cosmic.blue
    }
}

/// Engine domain → accent colour (for the cross-domain "TimeSense suggests" card).
func domainAccent(_ domain: String) -> Color {
    switch domain {
    case "health":   return Cosmic.green
    case "location": return Cosmic.cyan
    case "calendar": return Cosmic.violet
    default:         return Cosmic.blue
    }
}

/// The cosmic screen backdrop — near-black neutral navy with faint blue/violet corner glows.
struct CosmicBackground: View {
    var body: some View {
        ZStack {
            LinearGradient(colors: [Cosmic.base, Cosmic.deep], startPoint: .top, endPoint: .bottom)
            RadialGradient(colors: [Cosmic.glowBlue.opacity(0.10), .clear],
                           center: .topLeading, startRadius: 0, endRadius: 440)
            RadialGradient(colors: [Cosmic.glowViolet.opacity(0.10), .clear],
                           center: .topTrailing, startRadius: 0, endRadius: 440)
        }
        .ignoresSafeArea()
    }
}

/// The recommendation-card background: a dark navy base that blooms into the domain accent from the
/// top-right corner (behind the glyph) — matching the reference, not a full-bleed gradient.
struct HeroBackground: View {
    let accent: Color
    var body: some View {
        ZStack {
            LinearGradient(colors: [Cosmic.heroBaseTop, Cosmic.heroBaseBot],
                           startPoint: .topLeading, endPoint: .bottomTrailing)
            RadialGradient(colors: [accent.opacity(0.55), accent.opacity(0.14), .clear],
                           center: .topTrailing, startRadius: 0, endRadius: 330)
        }
    }
}

/// Neon edge-light stroke for primary cards (bright at top, fading down).
func neonEdge(_ accent: Color) -> LinearGradient {
    LinearGradient(colors: [.white.opacity(0.30), .white.opacity(0.05), accent.opacity(0.25)],
                   startPoint: .top, endPoint: .bottom)
}

/// A dark translucent glass pill for the signal chips on a hero card, with a domain-coloured icon.
struct HeroPill: View {
    let icon: String
    let text: String
    var tint: Color = .white

    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: icon).font(.caption2.weight(.semibold)).foregroundStyle(tint)
            Text(text).font(DesignTokens.Typography.caption.weight(.medium)).foregroundStyle(.white)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.ultraThinMaterial.opacity(0.4), in: Capsule())
        .background(Capsule().fill(Color.white.opacity(0.05)))
        .overlay(Capsule().stroke(Color.white.opacity(0.14), lineWidth: 1))
    }
}

/// A large glowing line-art style symbol, tinted to the recommendation's domain colour.
struct HeroGlyph: View {
    let systemName: String
    var tint: Color = .white

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: 40, weight: .regular))
            .foregroundStyle(tint)
            .shadow(color: tint.opacity(0.75), radius: 12)
            .shadow(color: tint.opacity(0.45), radius: 22)
    }
}

/// Frosted chrome for the primary recommendation card: neon edge + soft domain-coloured glow.
struct HeroCardChrome: ViewModifier {
    var glow: Color = Cosmic.glowViolet
    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
        content
            .clipShape(shape)
            .overlay(shape.stroke(neonEdge(glow), lineWidth: 1))
            .shadow(color: glow.opacity(0.30), radius: 26, x: 0, y: 12)
    }
}

extension View {
    func heroCardChrome(glow: Color = Cosmic.glowViolet) -> some View {
        modifier(HeroCardChrome(glow: glow))
    }
}
