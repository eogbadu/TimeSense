import SwiftUI

// Premium cosmic palette — matched to the reference: a near-black NEUTRAL navy base, dark slate
// cards, and recommendation cards that are DARK with a domain-coloured glow (not a bright gradient).
enum Cosmic {
    // Single base navy — must equal the `Background` colour asset so flat and cosmic screens match.
    static let base    = Color(red: 0.031, green: 0.043, blue: 0.078)  // #080B14 near-black navy
    static let deep    = Color(red: 0.020, green: 0.027, blue: 0.055)  // #05070E darkest (bottom)
    static let surface = Color(red: 0.067, green: 0.078, blue: 0.122)  // #11141F dark slate card

    // "Warmer dark" screen ground — lifted navy (top) into a deep navy (bottom), so Now/Today no
    // longer read as flat black. Paired with warm corner glows in CosmicBackground.
    static let baseWarm = Color(red: 0.071, green: 0.090, blue: 0.169)  // #12172B lifted navy
    static let deepWarm = Color(red: 0.039, green: 0.055, blue: 0.110)  // #0A0E1C deep navy

    // Dark navy base for the hero card (blooms into the domain colour top-right).
    static let heroBaseTop = Color(red: 0.055, green: 0.086, blue: 0.165) // #0E162A
    static let heroBaseBot = Color(red: 0.035, green: 0.051, blue: 0.106) // #090D1B

    // Semantic accents — a full warm→cool wheel used across the home screen (not just cool hues).
    static let green  = Color(red: 0.208, green: 0.839, blue: 0.627) // #35D6A0 health/energy
    static let blue   = Color(red: 0.239, green: 0.545, blue: 1.000) // #3D8BFF deep focus
    static let cyan   = Color(red: 0.141, green: 0.780, blue: 0.867) // #24C7DD low-focus/nearby
    static let violet = Color(red: 0.604, green: 0.420, blue: 1.000) // #9A6BFF meetings/appointments
    static let amber  = Color(red: 1.000, green: 0.706, blue: 0.302) // #FFB44D deadlines/planning/email
    static let orange = Color(red: 1.000, green: 0.549, blue: 0.259) // #FF8C42 errands/out & about
    static let red    = Color(red: 1.000, green: 0.420, blue: 0.420) // #FF6B6B overdue/urgent
    static let yellow = Color(red: 1.000, green: 0.835, blue: 0.310) // #FFD54F quick/personal

    static let glowBlue   = Color(red: 0.18, green: 0.39, blue: 1.00)
    static let glowViolet = Color(red: 0.48, green: 0.30, blue: 0.95)
    static let glowWarm   = Color(red: 1.00, green: 0.55, blue: 0.26)
}

/// Recommendation category → its accent colour (drives the hero glow, icon, and pills).
func heroAccent(_ descriptor: String) -> Color {
    switch descriptor {
    case "Health break":           return Cosmic.green
    case "Errand":                 return Cosmic.orange
    case "Chore":                  return Cosmic.yellow
    case "Appointment", "Meeting": return Cosmic.violet
    case "Focus task":             return Cosmic.blue
    case "Quick task", "Personal": return Cosmic.yellow
    case "Email":                  return Cosmic.amber
    case "Deadline":               return Cosmic.red
    default:                       return Cosmic.blue
    }
}

/// Engine domain → accent colour (for the cross-domain "TimeSense suggests" card).
func domainAccent(_ domain: String) -> Color {
    switch domain {
    case "health":   return Cosmic.green
    case "location": return Cosmic.orange   // out & about → warm
    case "calendar": return Cosmic.violet
    case "planning": return Cosmic.amber
    case "fallback": return Cosmic.cyan
    default:         return Cosmic.blue
    }
}

/// The cosmic screen backdrop — a "warmer dark" lifted navy with blue/violet corner glows and a warm
/// amber bloom from the bottom, so Now/Today feel rich rather than flat black.
struct CosmicBackground: View {
    @Environment(\.colorScheme) private var scheme

    // Soft light-cosmic ground: near-white gradient with very faint accent-tinted corner glows, so the
    // brand's atmosphere carries into light mode rather than reading as a flat white screen.
    private static let lightTop = Color(red: 0.968, green: 0.973, blue: 0.988)  // #F7F8FC
    private static let lightBot = Color(red: 0.925, green: 0.937, blue: 0.976)  // #ECEFF9

    var body: some View {
        ZStack {
            if scheme == .light {
                LinearGradient(colors: [Self.lightTop, Self.lightBot], startPoint: .top, endPoint: .bottom)
                RadialGradient(colors: [Cosmic.glowBlue.opacity(0.06), .clear],
                               center: .topLeading, startRadius: 0, endRadius: 460)
                RadialGradient(colors: [Cosmic.glowViolet.opacity(0.05), .clear],
                               center: .topTrailing, startRadius: 0, endRadius: 460)
                RadialGradient(colors: [Cosmic.glowWarm.opacity(0.05), .clear],
                               center: UnitPoint(x: 0.82, y: 1.04), startRadius: 0, endRadius: 480)
            } else {
                LinearGradient(colors: [Cosmic.baseWarm, Cosmic.deepWarm], startPoint: .top, endPoint: .bottom)
                RadialGradient(colors: [Cosmic.glowBlue.opacity(0.16), .clear],
                               center: .topLeading, startRadius: 0, endRadius: 460)
                RadialGradient(colors: [Cosmic.glowViolet.opacity(0.15), .clear],
                               center: .topTrailing, startRadius: 0, endRadius: 460)
                RadialGradient(colors: [Cosmic.glowWarm.opacity(0.13), .clear],
                               center: UnitPoint(x: 0.82, y: 1.04), startRadius: 0, endRadius: 480)
            }
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

/// A simple flowing layout that wraps its subviews onto new rows — keeps a chip row fully visible
/// (no horizontal scroll) instead of clipping items off-screen.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0
        for sv in subviews {
            let s = sv.sizeThatFits(.unspecified)
            if x + s.width > maxWidth && x > 0 { x = 0; y += rowHeight + spacing; rowHeight = 0 }
            x += s.width + spacing
            rowHeight = max(rowHeight, s.height)
        }
        return CGSize(width: maxWidth == .infinity ? x : maxWidth, height: y + rowHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) {
        var x = bounds.minX, y = bounds.minY, rowHeight: CGFloat = 0
        for sv in subviews {
            let s = sv.sizeThatFits(.unspecified)
            if x + s.width > bounds.maxX && x > bounds.minX { x = bounds.minX; y += rowHeight + spacing; rowHeight = 0 }
            sv.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(s))
            x += s.width + spacing
            rowHeight = max(rowHeight, s.height)
        }
    }
}
