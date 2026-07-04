import SwiftUI

struct CaptureView: View {
    @StateObject private var viewModel = CaptureViewModel()
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
                        .disabled(viewModel.uiState == .loading)

                    Button {
                        Task { await submitCapture() }
                    } label: {
                        if viewModel.uiState == .loading {
                            ProgressView()
                                .frame(maxWidth: .infinity)
                                .frame(height: 22)
                        } else {
                            Text("Capture")
                                .primaryButtonStyle()
                        }
                    }
                    .disabled(
                        captureText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            || viewModel.uiState == .loading
                    )
                    .opacity(
                        captureText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.4 : 1.0
                    )
                }
                .padding(.horizontal, DesignTokens.Spacing.md)

                statusView

                Spacer()
            }
            .background(DesignTokens.Color.background)
            .navigationTitle("Capture")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear { isInputFocused = true }
        }
    }

    @ViewBuilder
    private var statusView: some View {
        switch viewModel.uiState {
        case .idle, .loading:
            EmptyView()
        case .success(let title):
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                Text("Captured: \(title)")
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(1)
            }
            .padding(.horizontal, DesignTokens.Spacing.md)
            .transition(.opacity)
        case .error(let message):
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "exclamationmark.circle.fill")
                    .foregroundColor(DesignTokens.Color.destructive)
                Text(message)
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.destructive)
                    .lineLimit(2)
            }
            .padding(.horizontal, DesignTokens.Spacing.md)
            .transition(.opacity)
        }
    }

    private func submitCapture() async {
        let text = captureText
        await viewModel.submit(rawInput: text)
        if case .success = viewModel.uiState {
            captureText = ""
            isInputFocused = false
            // Auto-clear success banner after 3 seconds
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            viewModel.reset()
        }
    }
}
