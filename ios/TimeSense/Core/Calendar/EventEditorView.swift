import EventKit
import EventKitUI
import SwiftUI

/// Presents Apple's native "add event" editor pre-filled with a draft event. The user reviews it and
/// taps Add (or Cancel) — this IS the approval step, satisfying the "calendar writes require user
/// approval" rule. On save, `onComplete(true)` fires so the caller can re-sync.
struct EventEditorView: UIViewControllerRepresentable {
    let event: EKEvent
    let eventStore: EKEventStore
    let onComplete: (_ saved: Bool) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onComplete: onComplete) }

    func makeUIViewController(context: Context) -> EKEventEditViewController {
        let controller = EKEventEditViewController()
        controller.eventStore = eventStore
        controller.event = event
        controller.editViewDelegate = context.coordinator
        return controller
    }

    func updateUIViewController(_ controller: EKEventEditViewController, context: Context) {}

    final class Coordinator: NSObject, EKEventEditViewDelegate {
        private let onComplete: (Bool) -> Void
        init(onComplete: @escaping (Bool) -> Void) { self.onComplete = onComplete }

        func eventEditViewController(
            _ controller: EKEventEditViewController, didCompleteWith action: EKEventEditViewAction
        ) {
            controller.dismiss(animated: true)
            onComplete(action == .saved)
        }
    }
}
