import SwiftUI

struct CaptureView: View {
    @State private var captureText: String = ""
    @FocusState private var isInputFocused: Bool

    var body: some View {
        NavigationStack {
            VStack(spacing: DesignTokens.Spacing.lg) {
                Spacer()

                VStack(spacing: DesignTokens.Spacing.md) {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 48))
                        .foregroundColor(DesignTokens.Color.accent)

                    Text("What's on your mind?")
                        .font(DesignTokens.Typography.title2)
                        .foregroundColor(DesignTokens.Color.textPrimary)

                    Text("Speak or type — TimeSense will figure out the rest.")
                        .font(DesignTokens.Typography.callout)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, DesignTokens.Spacing.xl)
                }

                VStack(spacing: DesignTokens.Spacing.sm) {
                    TextField("e.g. Call dentist tomorrow at 2pm", text: $captureText, axis: .vertical)
                        .font(DesignTokens.Typography.body)
                        .padding(DesignTokens.Spacing.md)
                        .background(DesignTokens.Color.surface)
                        .cornerRadius(DesignTokens.Radius.lg)
                        .lineLimit(3...6)
                        .focused($isInputFocused)

                    Button(action: submitCapture) {
                        Text("Capture")
                            .primaryButtonStyle()
                    }
                    .disabled(captureText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    .opacity(captureText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.4 : 1.0)
                }
                .padding(.horizontal, DesignTokens.Spacing.md)

                Spacer()
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Capture")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear { isInputFocused = true }
        }
    }

    private func submitCapture() {
        // Connected to capture service in TIME-022+
        captureText = ""
    }
}
