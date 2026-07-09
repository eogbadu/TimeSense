import SwiftUI

struct CaptureView: View {
    @StateObject private var viewModel = CaptureViewModel()
    @StateObject private var voice = VoiceCaptureService()
    @State private var captureText: String = ""
    @State private var selectedChip: String?
    @FocusState private var isInputFocused: Bool

    private let chips = ["Task", "Reminder", "Schedule", "Errand", "Idea"]
    private let detectors: [(icon: String, label: String)] = [
        ("clock", "Time"),
        ("gauge.medium", "Priority"),
        ("tray.full.fill", "Task type"),
        ("checkmark.seal.fill", "Schedule fit"),
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignTokens.Spacing.lg) {
                    heroIcon.padding(.top, DesignTokens.Spacing.lg)

                    VStack(spacing: DesignTokens.Spacing.sm) {
                        Text("What's on your mind?")
                            .font(DesignTokens.Typography.title)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        Text("Speak or type naturally. TimeSense uses AI to turn it into tasks, reminders, and plans.")
                            .font(DesignTokens.Typography.callout)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, DesignTokens.Spacing.md)
                    }

                    inputBox
                    chipsRow
                    captureButton
                    statusView
                    detectSection
                }
                .padding(.horizontal, DesignTokens.Spacing.lg)
                .padding(.bottom, DesignTokens.Spacing.xxl)
            }
            .background(CosmicBackground())
            // Let the user swipe the keyboard down (the field is multi-line, so Return adds a
            // newline rather than dismissing).
            .scrollDismissesKeyboard(.interactively)
            .navigationTitle("Capture")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Image(systemName: "sparkles").foregroundColor(DesignTokens.Color.accent)
                }
                // A clear way to dismiss the keyboard so the Capture button + tab bar are reachable.
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") { isInputFocused = false }
                        .fontWeight(.semibold)
                }
            }
            .alert("Voice capture", isPresented: Binding(
                get: { voice.errorMessage != nil },
                set: { if !$0 { voice.errorMessage = nil } }
            )) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(voice.errorMessage ?? "")
            }
            // Live transcription streams into the input field while recording.
            .onChange(of: voice.transcript) { _, text in
                if voice.isRecording { captureText = text }
            }
        }
    }

    private var heroIcon: some View {
        ZStack {
            Circle()
                .fill(LinearGradient(colors: [Cosmic.blue, Cosmic.violet],
                                     startPoint: .topLeading, endPoint: .bottomTrailing))
                .frame(width: 110, height: 110)
                .overlay(Circle().stroke(Color.white.opacity(0.18), lineWidth: 1))
                .shadow(color: Cosmic.violet.opacity(voice.isRecording ? 0.6 : 0.4),
                        radius: voice.isRecording ? 30 : 22, y: 8)
                .shadow(color: Cosmic.blue.opacity(0.4), radius: 16, y: 2)
            if voice.isRecording {
                WaveformView(level: voice.level, color: .white)
            } else {
                Image(systemName: "waveform")
                    .font(.system(size: 40, weight: .semibold))
                    .foregroundColor(.white)
            }
        }
        .animation(.easeInOut(duration: 0.25), value: voice.isRecording)
    }

    private var inputBox: some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
            TextField("e.g. Call dentist tomorrow at 2pm", text: $captureText, axis: .vertical)
                .font(DesignTokens.Typography.body)
                .lineLimit(1...5)
                .focused($isInputFocused)
                .disabled(viewModel.uiState == .loading)
            Button {
                isInputFocused = false
                Task { await voice.toggle() }
            } label: {
                Image(systemName: voice.isRecording ? "stop.circle.fill" : "mic.fill")
                    .font(voice.isRecording ? .title2 : .body)
                    .foregroundColor(voice.isRecording ? DesignTokens.Color.destructive : DesignTokens.Color.accent)
                    .symbolEffect(.pulse, isActive: voice.isRecording)
            }
            .accessibilityLabel(voice.isRecording ? "Stop recording" : "Record voice")
        }
        .padding(DesignTokens.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous)
                .fill(DesignTokens.Color.surface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous)
                .stroke(DesignTokens.Color.textSecondary.opacity(0.15), lineWidth: 1)
        )
    }

    private var chipsRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: DesignTokens.Spacing.sm) {
                ForEach(chips, id: \.self) { chip in
                    let selected = selectedChip == chip
                    Button {
                        selectedChip = selected ? nil : chip
                    } label: {
                        Text(chip)
                            .font(DesignTokens.Typography.footnote.weight(.medium))
                            .foregroundColor(selected ? .white : DesignTokens.Color.accent)
                            .padding(.horizontal, DesignTokens.Spacing.md)
                            .padding(.vertical, DesignTokens.Spacing.sm)
                            .background(
                                Capsule().fill(selected ? DesignTokens.Color.accent : DesignTokens.Color.surface)
                            )
                            .overlay(Capsule().stroke(DesignTokens.Color.accent.opacity(0.4), lineWidth: 1))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 2)
        }
    }

    private var captureButton: some View {
        Button {
            Task { await submitCapture() }
        } label: {
            Group {
                if viewModel.uiState == .loading {
                    ProgressView().tint(.white)
                } else {
                    Text("Capture").font(DesignTokens.Typography.headline)
                }
            }
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, DesignTokens.Spacing.md)
            .background(Capsule().fill(DesignTokens.Color.accent))
        }
        .disabled(
            captureText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || viewModel.uiState == .loading
        )
        .opacity(captureText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.5 : 1.0)
    }

    private var detectSection: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("TimeSense can detect")
                .font(DesignTokens.Typography.headline)
                .foregroundColor(DesignTokens.Color.textPrimary)
            HStack(spacing: 0) {
                ForEach(detectors, id: \.label) { d in
                    VStack(spacing: DesignTokens.Spacing.xs) {
                        Image(systemName: d.icon)
                            .font(.title3)
                            .foregroundColor(DesignTokens.Color.accent)
                        Text(d.label)
                            .font(DesignTokens.Typography.caption)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, DesignTokens.Spacing.sm)
    }

    @ViewBuilder
    private var statusView: some View {
        switch viewModel.uiState {
        case .idle, .loading:
            EmptyView()
        case .success(let title):
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "checkmark.circle.fill").foregroundColor(.green)
                Text("Captured: \(title)")
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(1)
            }
            .transition(.opacity)
        case .error(let message):
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "exclamationmark.circle.fill").foregroundColor(DesignTokens.Color.destructive)
                Text(message)
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.destructive)
                    .lineLimit(2)
            }
            .transition(.opacity)
        }
    }

    private func submitCapture() async {
        let text = captureText
        await viewModel.submit(rawInput: text)
        if case .success = viewModel.uiState {
            captureText = ""
            selectedChip = nil
            isInputFocused = false
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            viewModel.reset()
        }
    }
}

/// An audio-reactive waveform shown while recording. Bar heights scale with the live mic level and
/// jitter per-bar for a lively look; collapses to a flat line in silence.
private struct WaveformView: View {
    let level: CGFloat        // 0…1 from VoiceCaptureService
    var color: Color = .white

    private let barCount = 7
    private let maxHeight: CGFloat = 46
    private let minHeight: CGFloat = 6
    @State private var jitter: [CGFloat] = Array(repeating: 0.6, count: 7)
    private let ticker = Timer.publish(every: 0.11, on: .main, in: .common).autoconnect()

    var body: some View {
        HStack(spacing: 5) {
            ForEach(0..<barCount, id: \.self) { i in
                Capsule()
                    .fill(color)
                    .frame(width: 5, height: barHeight(i))
            }
        }
        .frame(height: maxHeight)
        .animation(.easeInOut(duration: 0.11), value: level)
        .animation(.easeInOut(duration: 0.11), value: jitter)
        .onReceive(ticker) { _ in
            jitter = (0..<barCount).map { _ in CGFloat.random(in: 0.35...1.0) }
        }
    }

    private func barHeight(_ i: Int) -> CGFloat {
        // A gentle idle shimmer so it always looks alive while recording, plus a strong per-bar
        // reaction to how loudly you're speaking.
        let idle = 0.16 * jitter[i]
        let voice = level * (0.45 + 0.55 * jitter[i])
        let amount = min(1.0, idle + voice)
        return max(minHeight, maxHeight * amount)
    }
}
