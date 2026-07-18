import SwiftUI
import UIKit

/// Centralised design tokens — all colours, type, spacing, radius, animation in one place.
/// Never hardcode these values elsewhere; always reference via DesignTokens.
enum DesignTokens {

    // MARK: – Colour

    enum Color {
        /// Primary brand accent (violet-indigo — the "Sense" hue / ring's warm end)
        static let accent = SwiftUI.Color("AccentColor")
        /// Secondary accent (azure — the ring's cool end; time values, links, selected states)
        static let accentBlue = SwiftUI.Color("AccentBlue")
        /// Background (near-black cosmic navy in dark)
        static let background = SwiftUI.Color("Background")
        /// Secondary background / card surface
        static let surface = SwiftUI.Color("Surface")
        /// Primary text
        static let textPrimary = SwiftUI.Color("TextPrimary")
        /// Secondary / muted text
        static let textSecondary = SwiftUI.Color("TextSecondary")
        /// Destructive / warning
        static let destructive = SwiftUI.Color("Destructive")
        /// Success confirmation
        static let success = SwiftUI.Color("Success")
        /// Semantic energy/health (same green as success)
        static let energy = SwiftUI.Color("Success")
        /// Hairline border on cards — subtle white on dark, subtle black on light.
        static let hairline = SwiftUI.Color(uiColor: UIColor { trait in
            trait.userInterfaceStyle == .dark ? UIColor(white: 1, alpha: 0.08) : UIColor(white: 0, alpha: 0.08)
        })
        /// Text/icons that sit on the always-dark hero & accent surfaces (white in both schemes).
        static let onHero = SwiftUI.Color.white
    }

    // MARK: – Gradients & glow (the cosmic brand, sampled from the app icon)

    enum Gradient {
        /// The signature blue→violet sweep (the ring). Used for the hero recommendation card.
        static let hero = LinearGradient(
            colors: [Color.accentBlue, Color.accent],
            startPoint: .topLeading, endPoint: .bottomTrailing
        )
        /// A soft cosmic wash for screen backgrounds — near-black navy deepening downward.
        static let screen = LinearGradient(
            colors: [SwiftUI.Color(red: 0.05, green: 0.06, blue: 0.12),
                     SwiftUI.Color(red: 0.03, green: 0.03, blue: 0.07)],
            startPoint: .top, endPoint: .bottom
        )
    }

    enum Glow {
        /// Accent halo for the hero card / active elements.
        static let accent = (color: DesignTokens.Color.accent.opacity(0.45), radius: 28.0, y: 10.0)
        static let subtle = (color: DesignTokens.Color.accentBlue.opacity(0.30), radius: 18.0, y: 6.0)
    }

    // MARK: – Typography

    // Refined SF Pro scale — clean, Apple-like hierarchy (headings use the default face, not rounded,
    // for a calmer, more premium read). Apply `.tracking(Tracking.tight)` on large headings in views.
    enum Typography {
        static let largeTitle   = SwiftUI.Font.system(size: 34, weight: .bold,      design: .default)
        static let title        = SwiftUI.Font.system(size: 28, weight: .bold,      design: .default)
        static let title2       = SwiftUI.Font.system(size: 22, weight: .semibold,  design: .default)
        static let headline     = SwiftUI.Font.system(size: 17, weight: .semibold,  design: .default)
        static let body         = SwiftUI.Font.system(size: 17, weight: .regular,   design: .default)
        static let callout      = SwiftUI.Font.system(size: 16, weight: .regular,   design: .default)
        static let subheadline  = SwiftUI.Font.system(size: 15, weight: .regular,   design: .default)
        static let footnote     = SwiftUI.Font.system(size: 13, weight: .regular,   design: .default)
        static let caption      = SwiftUI.Font.system(size: 12, weight: .medium,    design: .default)
    }

    enum Tracking {
        static let tight: CGFloat = -0.5   // large headings
        static let wide: CGFloat = 0.6     // uppercase section labels
    }

    // MARK: – Spacing

    enum Spacing {
        static let xs: CGFloat  = 4
        static let sm: CGFloat  = 8
        static let md: CGFloat  = 16
        static let lg: CGFloat  = 24
        static let xl: CGFloat  = 32
        static let xxl: CGFloat = 48
    }

    // MARK: – Corner radius

    enum Radius {
        static let sm: CGFloat  = 8
        static let md: CGFloat  = 12
        static let lg: CGFloat  = 16
        static let xl: CGFloat  = 24
        static let pill: CGFloat = 999
    }

    // MARK: – Animation

    enum Animation {
        static let standard  = SwiftUI.Animation.spring(response: 0.35, dampingFraction: 0.75)
        static let fast      = SwiftUI.Animation.spring(response: 0.2,  dampingFraction: 0.8)
        static let gentle    = SwiftUI.Animation.easeInOut(duration: 0.4)
    }

    // MARK: – Shadow

    // Soft, diffuse shadows — cards should feel like they float, not be outlined.
    enum Shadow {
        static let card  = (color: SwiftUI.Color.black.opacity(0.05), radius: 18.0, x: 0.0, y: 8.0)
        static let float = (color: SwiftUI.Color.black.opacity(0.10), radius: 28.0, x: 0.0, y: 12.0)
    }
}
