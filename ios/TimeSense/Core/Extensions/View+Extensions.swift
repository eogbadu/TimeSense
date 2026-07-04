import SwiftUI

extension View {
    /// Conditionally apply a transformation
    @ViewBuilder
    func `if`<Content: View>(_ condition: Bool, transform: (Self) -> Content) -> some View {
        if condition { transform(self) } else { self }
    }

    /// Hide a view without removing it from the hierarchy (preserves layout)
    func hidden(_ isHidden: Bool) -> some View {
        opacity(isHidden ? 0 : 1)
    }
}
