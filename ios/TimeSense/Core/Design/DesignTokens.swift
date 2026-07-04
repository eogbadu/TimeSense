import SwiftUI

/// Centralised design tokens — all colours, type, spacing, radius, animation in one place.
/// Never hardcode these values elsewhere; always reference via DesignTokens.
enum DesignTokens {

    // MARK: – Colour

    enum Color {
        /// Primary brand accent (deep indigo)
        static let accent = SwiftUI.Color("AccentColor")
        /// Background
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
    }

    // MARK: – Typography

    enum Typography {
        static let largeTitle   = SwiftUI.Font.system(size: 34, weight: .bold, design: .rounded)
        static let title        = SwiftUI.Font.system(size: 28, weight: .semibold, design: .rounded)
        static let title2       = SwiftUI.Font.system(size: 22, weight: .semibold, design: .rounded)
        static let headline     = SwiftUI.Font.system(size: 17, weight: .semibold, design: .default)
        static let body         = SwiftUI.Font.system(size: 17, weight: .regular, design: .default)
        static let callout      = SwiftUI.Font.system(size: 16, weight: .regular, design: .default)
        static let subheadline  = SwiftUI.Font.system(size: 15, weight: .regular, design: .default)
        static let footnote     = SwiftUI.Font.system(size: 13, weight: .regular, design: .default)
        static let caption      = SwiftUI.Font.system(size: 12, weight: .regular, design: .default)
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

    enum Shadow {
        static let card  = (color: SwiftUI.Color.black.opacity(0.08), radius: 12.0, x: 0.0, y: 4.0)
        static let float = (color: SwiftUI.Color.black.opacity(0.14), radius: 20.0, x: 0.0, y: 8.0)
    }
}
