import SwiftUI

struct CaptureView: View {
    @StateObject private var viewModel = CaptureViewModel()
    @StateObject private var voice = VoiceCaptureService()
    @State private var captureText: String = ""
    @State private var selectedChip: String?
    // Contextual inputs revealed by the Reminder / Schedule / Errand chips.
    @State private var pickedDate = Calendar.current.date(byAdding: .hour, value: 1, to: Date()) ?? Date()
    @State private var includeTime = false
    @State private var locationQuery = ""
    @State private var pickedLocation: PlaceSearchResult?
    @State private var placeSearchTask: Task<Void, Never>?
    @FocusState private var isInputFocused: Bool

    private let chips: [(label: String, icon: String, color: Color)] = [
        ("Task", "checkmark.circle.fill", Cosmic.blue),
        ("Reminder", "bell.fill", Cosmic.amber),
        ("Schedule", "calendar", Cosmic.violet),
        ("Errand", "cart.fill", Cosmic.cyan),
        ("Idea", "lightbulb.fill", Cosmic.green),
    ]
    private let detectors: [(icon: String, label: String, color: Color)] = [
        ("clock.fill", "Time", Cosmic.blue),
        ("gauge.medium", "Priority", Cosmic.amber),
        ("tray.full.fill", "Task type", Cosmic.violet),
        ("checkmark.seal.fill", "Schedule fit", Cosmic.green),
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
                    if let chip = selectedChip { contextualInput(for: chip) }
                    captureButton
                    statusView
                    detectSection
                }
                .padding(.horizontal, DesignTokens.Spacing.lg)
                .padding(.bottom, 96)   // clear the custom tab bar (content can scroll under it in the pager)
                // Tap anywhere outside the input (empty space) to dismiss the keyboard. The field,
                // chips, and buttons handle their own taps first, so only empty-space taps land here.
                .contentShape(Rectangle())
                .onTapGesture { isInputFocused = false }
            }
            .background(CosmicBackground())
            // Let the user swipe the keyboard down (the field is multi-line, so Return adds a
            // newline rather than dismissing).
            .scrollDismissesKeyboard(.interactively)
            .navigationTitle("Capture")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
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
            // When the type changes, default a sensible input and clear the previous one.
            .onChange(of: selectedChip) { _, chip in
                includeTime = (chip == "Reminder")
                pickedLocation = nil
                locationQuery = ""
                viewModel.placeResults = []
            }
            .animation(DesignTokens.Animation.standard, value: selectedChip)
            .animation(DesignTokens.Animation.standard, value: viewModel.lastCaptured?.id)
        }
    }

    @ViewBuilder
    private func contextualInput(for chip: String) -> some View {
        switch chip {
        case "Reminder", "Schedule": dateTimeInput
        case "Errand":               errandInput
        default:                     EmptyView()
        }
    }

    // Reminder / Schedule → a date, with an optional time (never a required form).
    private var dateTimeInput: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "calendar").foregroundColor(Cosmic.violet)
                DatePicker("", selection: $pickedDate,
                           displayedComponents: includeTime ? [.date, .hourAndMinute] : [.date])
                    .labelsHidden()
                Spacer(minLength: 0)
            }
            Toggle(isOn: $includeTime) {
                Text("Add a time")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            .tint(Cosmic.violet)
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }

    // Errand → a location, autocompleting from saved places + maps.
    private var errandInput: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack(spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "mappin.and.ellipse").foregroundColor(Cosmic.cyan)
                TextField("Where? e.g. Walmart", text: $locationQuery)
                    .onChange(of: locationQuery) { _, q in
                        if pickedLocation?.name != q { pickedLocation = nil }
                        placeSearchTask?.cancel()
                        placeSearchTask = Task {
                            try? await Task.sleep(nanoseconds: 300_000_000)
                            if Task.isCancelled { return }
                            let near = LocationService.shared.currentLocation.map {
                                (lat: $0.coordinate.latitude, lng: $0.coordinate.longitude)
                            }
                            await viewModel.searchPlaces(q, near: near)
                        }
                    }
                if pickedLocation != nil {
                    Image(systemName: "checkmark.circle.fill").foregroundColor(Cosmic.green)
                }
            }
            if pickedLocation == nil {
                ForEach(viewModel.placeResults) { r in
                    Button {
                        pickedLocation = r; locationQuery = r.name; viewModel.placeResults = []
                        isInputFocused = false
                    } label: {
                        HStack(spacing: DesignTokens.Spacing.sm) {
                            Image(systemName: r.source == "saved" ? "star.fill" : "mappin")
                                .font(.caption)
                                .foregroundColor(r.source == "saved" ? Cosmic.amber : Cosmic.cyan)
                            VStack(alignment: .leading, spacing: 1) {
                                Text(r.name).font(DesignTokens.Typography.callout)
                                    .foregroundColor(DesignTokens.Color.textPrimary)
                                if let a = r.address {
                                    Text(a).font(DesignTokens.Typography.caption)
                                        .foregroundColor(DesignTokens.Color.textSecondary).lineLimit(1)
                                }
                            }
                            Spacer(minLength: 0)
                        }
                        .padding(.vertical, 4)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
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
                .onChange(of: captureText) { _, v in
                    if v.count > 2000 { captureText = String(v.prefix(2000)) }  // match the backend cap
                    // Starting a new capture clears the previous "detected" results (back to the tiles).
                    if !v.isEmpty && viewModel.lastCaptured != nil { viewModel.reset() }
                }
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

    // A fixed, fully-visible chip row (wraps to 2 rows). Tapping one tags the capture with a type
    // hint that biases how TimeSense parses it.
    private var chipsRow: some View {
        FlowLayout(spacing: DesignTokens.Spacing.sm) {
            ForEach(chips, id: \.label) { chip in
                let selected = selectedChip == chip.label
                Button {
                    selectedChip = selected ? nil : chip.label
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: chip.icon).font(.caption2.weight(.semibold))
                        Text(chip.label).font(DesignTokens.Typography.footnote.weight(.medium))
                    }
                    .foregroundColor(selected ? .white : chip.color)
                    .padding(.horizontal, DesignTokens.Spacing.md)
                    .padding(.vertical, DesignTokens.Spacing.sm)
                    .background(Capsule().fill(selected ? chip.color : chip.color.opacity(0.14)))
                    .overlay(Capsule().stroke(chip.color.opacity(selected ? 0 : 0.5), lineWidth: 1))
                }
                .buttonStyle(.plain)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
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

    // Idle → what TimeSense can pull out of natural language (onboarding). After a capture → what it
    // actually detected from that input, so the value is shown, not just promised.
    @ViewBuilder
    private var detectSection: some View {
        if let task = viewModel.lastCaptured {
            detectedSection(task)
        } else {
            capabilitySection
        }
    }

    private var capabilitySection: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("TimeSense can detect")
                .font(DesignTokens.Typography.headline)
                .foregroundColor(DesignTokens.Color.textPrimary)
            HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
                ForEach(detectors, id: \.label) { d in
                    DetectTile(icon: d.icon, color: d.color, primary: d.label, secondary: nil)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, DesignTokens.Spacing.sm)
    }

    private func detectedSection(_ task: CapturedTask) -> some View {
        let style = taskCategoryStyle(for: task.title)
        let items: [(icon: String, label: String, value: String, color: Color)] = [
            ("clock.fill", "Time", detectedTimeText(task), Cosmic.blue),
            ("gauge.medium", "Priority", priorityText(task.priority), Cosmic.amber),
            (style.icon, "Task type", style.descriptor, style.color),
            ("checkmark.seal.fill", "Schedule fit", scheduleFitText(task), Cosmic.green),
        ]
        return VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("TimeSense detected")
                .font(DesignTokens.Typography.headline)
                .foregroundColor(DesignTokens.Color.textPrimary)
            HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
                ForEach(items, id: \.label) { it in
                    DetectTile(icon: it.icon, color: it.color, primary: it.value, secondary: it.label)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, DesignTokens.Spacing.sm)
        .transition(.opacity)
    }

    private func priorityText(_ p: Int) -> String {
        p <= 2 ? "High" : (p == 3 ? "Medium" : "Low")
    }

    private func detectedTimeText(_ task: CapturedTask) -> String {
        if let start = task.scheduledStart { return Self.dayTime(start, showTimeAtMidnight: true) }
        if let due = task.dueAt { return Self.dayTime(due, showTimeAtMidnight: false) }
        return "Anytime"
    }

    private func scheduleFitText(_ task: CapturedTask) -> String {
        (task.autoScheduled || task.scheduledStart != nil) ? "Added to your day" : "In your list"
    }

    /// "Today 2:00 PM" / "Tomorrow 9:00 AM" / "Aug 3". Date-only dues (midnight) drop the time.
    private static func dayTime(_ date: Date, showTimeAtMidnight: Bool) -> String {
        let cal = Calendar.current
        let day: String
        if cal.isDateInToday(date) { day = "Today" }
        else if cal.isDateInTomorrow(date) { day = "Tomorrow" }
        else { day = date.formatted(.dateTime.month(.abbreviated).day()) }
        let isMidnight = cal.component(.hour, from: date) == 0 && cal.component(.minute, from: date) == 0
        if isMidnight && !showTimeAtMidnight { return day }
        return "\(day) \(date.formatted(date: .omitted, time: .shortened))"
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
        // Dismiss the keyboard UP FRONT — before the field disables during loading. Otherwise SwiftUI
        // restores focus when the field re-enables on success (the keyboard "pops back up"), covering
        // the "TimeSense detected" results at the bottom of the screen so you never see them appear.
        isInputFocused = false
        // Explicit inputs win over the parse. Reminder/Schedule → time or date-only; Errand → place.
        var scheduledAt: Date?
        var dueAt: Date?
        if selectedChip == "Reminder" || selectedChip == "Schedule" {
            if includeTime { scheduledAt = pickedDate }
            else { dueAt = Calendar.current.startOfDay(for: pickedDate) }
        }
        await viewModel.submit(
            rawInput: text, typeHint: selectedChip,
            scheduledAt: scheduledAt, dueAt: dueAt, location: pickedLocation
        )
        if case .success = viewModel.uiState {
            captureText = ""
            selectedChip = nil
            pickedLocation = nil
            locationQuery = ""
            includeTime = false
            // The keyboard is already down (above), so the detected results animate in on a fully
            // visible screen. They stay up until the user starts the next capture (onChange below).
        }
    }
}

/// One tile in the detect row. With no `secondary` it's the idle capability label (e.g. "Priority");
/// with a `secondary` it shows the detected value on top ("High") and the category below ("Priority").
private struct DetectTile: View {
    let icon: String
    let color: Color
    let primary: String
    let secondary: String?

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.sm) {
            RoundedRectangle(cornerRadius: DesignTokens.Radius.md, style: .continuous)
                .fill(color.opacity(0.16))
                .frame(width: 48, height: 48)
                .overlay(Image(systemName: icon).font(.title3).foregroundColor(color))
            Text(primary)
                .font(DesignTokens.Typography.caption.weight(secondary == nil ? .regular : .semibold))
                .foregroundColor(secondary == nil ? DesignTokens.Color.textSecondary : DesignTokens.Color.textPrimary)
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .minimumScaleFactor(0.75)
            if let secondary {
                Text(secondary)
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .lineLimit(1)
            }
        }
        .frame(maxWidth: .infinity)
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
