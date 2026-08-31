import AVFoundation
import Foundation
import OSLog
import Speech

/// Why a recording session couldn't start or couldn't continue. Distinct cases exist so the UI can
/// say something actionable instead of one catch-all string — a dead microphone and a denied
/// permission need different things from the user.
enum VoiceCaptureError: Error, Equatable {
    case sessionUnavailable      // couldn't configure/activate AVAudioSession
    case noAudioInput            // the input node reported an unusable format (0 Hz / 0 channels)
    case engineFailed            // AVAudioEngine.start() threw
    case heardNothing            // engine started, but no buffer ever arrived
    case recognitionUnavailable  // the recognizer failed repeatedly, not just between segments

    /// User-facing copy. Every one of these used to be a silent no-op or "Couldn't start recording."
    var message: String {
        switch self {
        case .sessionUnavailable:
            return "Couldn't start recording. Another app may be using audio."
        case .noAudioInput, .heardNothing:
            return "TimeSense can't hear the microphone. Check that no other app is using it, then try again."
        case .engineFailed:
            return "Couldn't start recording."
        case .recognitionUnavailable:
            return "Speech recognition stopped working. Your text so far has been kept."
        }
    }
}

/// A box the real-time audio thread can touch without reaching into `@MainActor` state.
///
/// The tap closure runs on CoreAudio's render thread, so it must not read actor-isolated properties
/// (it did, before TIME-314 — a genuine data race that only compiled because the target is still on
/// Swift 5 language mode). Everything the tap needs lives here behind a lock instead.
private final class AudioTapState: @unchecked Sendable {
    private let lock = NSLock()
    private var _request: SFSpeechAudioBufferRecognitionRequest?
    private var _sawFirstBuffer = false

    var request: SFSpeechAudioBufferRecognitionRequest? {
        get { lock.lock(); defer { lock.unlock() }; return _request }
        set { lock.lock(); _request = newValue; lock.unlock() }
    }

    var sawFirstBuffer: Bool {
        lock.lock(); defer { lock.unlock() }; return _sawFirstBuffer
    }

    /// Marks a buffer as seen and reports whether this was the first one, so the caller can log the
    /// transition exactly once without a second round of locking.
    func markBufferReceived() -> Bool {
        lock.lock(); defer { lock.unlock() }
        if _sawFirstBuffer { return false }
        _sawFirstBuffer = true
        return true
    }

    func reset() {
        lock.lock(); _request = nil; _sawFirstBuffer = false; lock.unlock()
    }
}

/// On-device speech-to-text for the Capture screen, built for *continuous* dictation: the audio
/// engine runs until the user taps stop, and each time the recognizer finalizes a segment after a
/// pause we commit that text and seamlessly start a new segment — so pausing never stops recording
/// or wipes what was already said. Recognition stays on-device where supported; we never persist or
/// upload raw audio, only the transcript, which flows into the normal capture pipeline.
///
/// TIME-314: the engine is rebuilt for every session and every failure is now reported. Previously a
/// single process-lifetime `AVAudioEngine` was reused, and `start()` succeeding was taken as proof
/// of a live microphone — so a stale cached input format left the UI recording nothing, forever,
/// with no error. See `decision_log.md`.
@MainActor
final class VoiceCaptureService: ObservableObject {
    @Published private(set) var transcript = ""
    @Published private(set) var isRecording = false
    @Published private(set) var level: CGFloat = 0   // 0…1 mic loudness, drives the waveform
    @Published var errorMessage: String?

    private let recognizer = SFSpeechRecognizer(locale: Locale.current)
    private let log = Logger(subsystem: "com.timesense", category: "voice")

    /// Rebuilt per session — never reused across start/stop. See the type comment.
    private var audioEngine = AVAudioEngine()
    private let tapState = AudioTapState()

    private var task: SFSpeechRecognitionTask?
    private var committed = ""   // finalized text from earlier segments in this session
    private var watchdog: Task<Void, Never>?
    private var observers: [NSObjectProtocol] = []

    /// A recognizer that fails permanently would otherwise restart forever (it did, before TIME-314).
    private var restartTimes: [Date] = []
    private static let restartWindow: TimeInterval = 10
    private static let maxRestartsInWindow = 4

    /// How long a started engine may go without delivering a buffer before we call it dead.
    private static let firstBufferTimeout: TimeInterval = 1.5

    /// Publishing every buffer would hop to the MainActor ~43×/second at 1024 frames; the waveform
    /// re-renders on its own 0.11s ticker, so a third of that is plenty.
    private static let levelPublishInterval = 3

    func toggle() async {
        if isRecording { stop() } else { await start() }
    }

    func start() async {
        errorMessage = nil
        guard await requestPermissions() else {
            errorMessage = "Enable microphone and speech recognition in Settings ▸ TimeSense."
            return
        }
        guard let recognizer, recognizer.isAvailable else {
            errorMessage = "Speech recognition isn't available right now."
            return
        }
        committed = ""
        transcript = ""
        restartTimes = []
        do {
            try startAudio()
            isRecording = true
            observeSessionChanges()
            startRecognition()
            startWatchdog()
        } catch let error as VoiceCaptureError {
            log.error("start failed: \(String(describing: error), privacy: .public)")
            errorMessage = error.message
            teardown()
        } catch {
            log.error("start failed: \(error.localizedDescription, privacy: .public)")
            errorMessage = VoiceCaptureError.engineFailed.message
            teardown()
        }
    }

    func stop() {
        isRecording = false
        level = 0
        teardown()
    }

    /// Ends the session because it can't continue, leaving whatever was already transcribed in place.
    private func fail(_ error: VoiceCaptureError) {
        guard isRecording else { return }
        log.error("session failed: \(String(describing: error), privacy: .public)")
        stop()
        errorMessage = error.message
    }

    // MARK: - Audio (runs for the whole session)

    private func startAudio() throws {
        // Start from a clean graph every time. Reusing one engine across sessions lets the input
        // node hold a format resolved under an older hardware route; the tap then installs cleanly,
        // the engine starts without throwing, and no buffer ever arrives.
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        audioEngine.reset()
        audioEngine = AVAudioEngine()
        tapState.reset()

        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.record, mode: .measurement, options: [.duckOthers, .allowBluetooth])
            try session.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            log.error("audio session setup failed: \(error.localizedDescription, privacy: .public)")
            throw VoiceCaptureError.sessionUnavailable
        }

        // Read the format only after the session is active, so it reflects the live route.
        let input = audioEngine.inputNode
        let format = input.outputFormat(forBus: 0)
        log.info("input format: \(format.sampleRate, privacy: .public)Hz \(format.channelCount, privacy: .public)ch")
        guard Self.isUsableInputFormat(format) else {
            throw VoiceCaptureError.noAudioInput
        }

        let state = tapState
        let interval = Self.levelPublishInterval
        var bufferCount = 0
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            // Audio render thread: touch only `state`, never actor-isolated properties.
            state.request?.append(buffer)
            let isFirst = state.markBufferReceived()
            bufferCount &+= 1
            guard isFirst || bufferCount % interval == 0 else { return }
            let lvl = Self.rmsLevel(buffer)
            Task { @MainActor [weak self] in
                guard let self else { return }
                if isFirst { self.log.info("first audio buffer received") }
                self.level = lvl
            }
        }
        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            log.error("engine start failed: \(error.localizedDescription, privacy: .public)")
            throw VoiceCaptureError.engineFailed
        }
        log.info("audio engine started")
    }

    /// A started engine is not a live microphone — if nothing arrives shortly after start, say so
    /// rather than leaving the user talking at a waveform that will never move.
    private func startWatchdog() {
        watchdog?.cancel()
        watchdog = Task { @MainActor [weak self] in
            guard let self else { return }
            try? await Task.sleep(nanoseconds: UInt64(Self.firstBufferTimeout * 1_000_000_000))
            guard !Task.isCancelled, self.isRecording, !self.tapState.sawFirstBuffer else { return }
            self.fail(.heardNothing)
        }
    }

    /// A call, a Siri invocation or AirPods connecting mid-sentence all kill the input while the
    /// engine still believes it is running. Rebuild the graph and keep the text already committed.
    private func observeSessionChanges() {
        let center = NotificationCenter.default
        let session = AVAudioSession.sharedInstance()

        observers.append(center.addObserver(
            forName: AVAudioSession.interruptionNotification, object: session, queue: .main
        ) { [weak self] note in
            guard let raw = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                  let type = AVAudioSession.InterruptionType(rawValue: raw) else { return }
            let options = (note.userInfo?[AVAudioSessionInterruptionOptionKey] as? UInt)
                .map(AVAudioSession.InterruptionOptions.init(rawValue:)) ?? []
            Task { @MainActor in
                guard let self, self.isRecording else { return }
                switch type {
                case .began:
                    self.log.info("audio interrupted")
                case .ended where options.contains(.shouldResume):
                    self.log.info("interruption ended — restarting audio")
                    self.restartAudio()
                default:
                    // Ended but not resumable — something else holds the session.
                    self.fail(.sessionUnavailable)
                }
            }
        })

        observers.append(center.addObserver(
            forName: AVAudioSession.routeChangeNotification, object: session, queue: .main
        ) { [weak self] note in
            guard let raw = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
                  let reason = AVAudioSession.RouteChangeReason(rawValue: raw) else { return }
            guard reason == .oldDeviceUnavailable || reason == .newDeviceAvailable else { return }
            Task { @MainActor in
                guard let self, self.isRecording else { return }
                self.log.info("route changed (\(reason.rawValue, privacy: .public)) — restarting audio")
                self.restartAudio()
            }
        })
    }

    /// Rebuilds the audio graph mid-session, preserving `committed` so the user keeps what they said.
    private func restartAudio() {
        committed = transcript
        task?.cancel()
        task = nil
        tapState.request = nil
        do {
            try startAudio()
            startRecognition()
            startWatchdog()
        } catch let error as VoiceCaptureError {
            fail(error)
        } catch {
            fail(.engineFailed)
        }
    }

    // MARK: - Recognition (restarts per segment, without touching the audio engine)

    private func startRecognition() {
        guard let recognizer, isRecording else { return }
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        if recognizer.supportsOnDeviceRecognition {
            req.requiresOnDeviceRecognition = true   // keep audio on-device (privacy)
        }
        tapState.request = req

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            Task { @MainActor in
                guard let self, self.isRecording else { return }
                if let result {
                    let segment = result.bestTranscription.formattedString
                    self.transcript = Self.join(self.committed, segment)
                    if result.isFinal {
                        // Commit this segment and immediately continue a new one (seamless dictation).
                        self.committed = self.transcript
                        self.restartRecognition()
                    }
                } else if let error {
                    // Usually just a segment ending on a long pause — but a recognizer that has
                    // genuinely stopped working would otherwise restart forever, so it is capped.
                    self.log.info("recognition segment ended: \(error.localizedDescription, privacy: .public)")
                    self.committed = self.transcript
                    self.restartRecognition()
                }
            }
        }
    }

    private func restartRecognition() {
        guard isRecording else { return }
        guard Self.allowsRestart(now: Date(), history: &restartTimes,
                                 window: Self.restartWindow, limit: Self.maxRestartsInWindow) else {
            fail(.recognitionUnavailable)
            return
        }
        tapState.request?.endAudio()
        tapState.request = nil
        task?.finish()
        task = nil
        startRecognition()
    }

    private func teardown() {
        watchdog?.cancel()
        watchdog = nil
        for observer in observers { NotificationCenter.default.removeObserver(observer) }
        observers = []

        if audioEngine.isRunning { audioEngine.stop() }
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.reset()

        tapState.request?.endAudio()
        tapState.reset()
        task?.cancel()
        task = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    // MARK: - Pure helpers (unit-tested in VoiceCaptureServiceTests)
    //
    // `nonisolated` because the audio render thread calls rmsLevel, and because pure logic
    // should be testable without hopping to the main actor.

    nonisolated static func join(_ committed: String, _ segment: String) -> String {
        if committed.isEmpty { return segment }
        if segment.isEmpty { return committed }
        return committed + " " + segment
    }

    /// A microphone that produced no usable route reports 0 Hz or 0 channels. Installing a tap with
    /// such a format succeeds and then silently delivers nothing, so it is rejected up front.
    nonisolated static func isUsableInputFormat(_ format: AVAudioFormat) -> Bool {
        format.sampleRate > 0 && format.channelCount > 0
    }

    /// Records a restart and reports whether it is still within the allowed rate. Prunes the history
    /// to `window` so ordinary pause-driven restarts across a long dictation never trip the cap.
    nonisolated static func allowsRestart(now: Date, history: inout [Date],
                              window: TimeInterval, limit: Int) -> Bool {
        history = history.filter { now.timeIntervalSince($0) < window }
        history.append(now)
        return history.count <= limit
    }

    /// Normalized loudness (0…1) of a capture buffer, for the waveform.
    ///
    /// Speech RMS sits very low — ordinary conversation is around 0.02 — so the raw value is scaled
    /// and then curved. A linear scale (what this was before TIME-315) spends most of its range on
    /// volumes nobody produces, leaving normal speech bunched near the floor and barely visible. The
    /// exponent expands the quiet end where voices actually live and compresses the top, which is
    /// what makes the bars track speech rather than only shouting.
    nonisolated static func rmsLevel(_ buffer: AVAudioPCMBuffer) -> CGFloat {
        guard let channel = buffer.floatChannelData?[0] else { return 0 }
        let n = Int(buffer.frameLength)
        guard n > 0 else { return 0 }
        var sum: Float = 0
        for i in 0..<n { let s = channel[i]; sum += s * s }
        let rms = sqrt(sum / Float(n))
        let scaled = min(1.0, max(0.0, Double(rms) * 24))
        return CGFloat(pow(scaled, 0.65))
    }

    private func requestPermissions() async -> Bool {
        let speechAuthorized: Bool = await withCheckedContinuation { cont in
            SFSpeechRecognizer.requestAuthorization { cont.resume(returning: $0 == .authorized) }
        }
        guard speechAuthorized else { return false }

        if #available(iOS 17.0, *) {
            return await AVAudioApplication.requestRecordPermission()
        } else {
            return await withCheckedContinuation { cont in
                AVAudioSession.sharedInstance().requestRecordPermission { cont.resume(returning: $0) }
            }
        }
    }
}
