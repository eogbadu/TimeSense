import AVFoundation
import Foundation
import Speech

/// On-device speech-to-text for the Capture screen, built for *continuous* dictation: the audio
/// engine runs until the user taps stop, and each time the recognizer finalizes a segment after a
/// pause we commit that text and seamlessly start a new segment — so pausing never stops recording
/// or wipes what was already said. Recognition stays on-device where supported; we never persist or
/// upload raw audio, only the transcript, which flows into the normal capture pipeline.
@MainActor
final class VoiceCaptureService: ObservableObject {
    @Published private(set) var transcript = ""
    @Published private(set) var isRecording = false
    @Published private(set) var level: CGFloat = 0   // 0…1 mic loudness, drives the waveform
    @Published var errorMessage: String?

    private let recognizer = SFSpeechRecognizer(locale: Locale.current)
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    private var committed = ""   // finalized text from earlier segments in this session

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
        do {
            try startAudio()
            isRecording = true
            startRecognition()
        } catch {
            errorMessage = "Couldn't start recording."
            teardown()
        }
    }

    func stop() {
        isRecording = false
        level = 0
        teardown()
    }

    // MARK: - Audio (runs for the whole session)

    private func startAudio() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: .duckOthers)
        try session.setActive(true, options: .notifyOthersOnDeactivation)

        let input = audioEngine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            guard let self else { return }
            self.request?.append(buffer)
            let lvl = Self.rmsLevel(buffer)
            Task { @MainActor in self.level = lvl }
        }
        audioEngine.prepare()
        try audioEngine.start()
    }

    // MARK: - Recognition (restarts per segment, without touching the audio engine)

    private func startRecognition() {
        guard let recognizer, isRecording else { return }
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        if recognizer.supportsOnDeviceRecognition {
            req.requiresOnDeviceRecognition = true   // keep audio on-device (privacy)
        }
        request = req

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            Task { @MainActor in
                guard let self else { return }
                if let result {
                    let segment = result.bestTranscription.formattedString
                    self.transcript = Self.join(self.committed, segment)
                    if result.isFinal {
                        // Commit this segment and immediately continue a new one (seamless dictation).
                        self.committed = self.transcript
                        if self.isRecording { self.restartRecognition() }
                    }
                } else if error != nil, self.isRecording {
                    // A segment ended (e.g. a long pause) — keep the session going.
                    self.committed = self.transcript
                    self.restartRecognition()
                }
            }
        }
    }

    private func restartRecognition() {
        task?.finish()
        task = nil
        request = nil
        startRecognition()
    }

    private func teardown() {
        if audioEngine.isRunning { audioEngine.stop() }
        audioEngine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        task?.cancel()
        request = nil
        task = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    private static func join(_ committed: String, _ segment: String) -> String {
        if committed.isEmpty { return segment }
        if segment.isEmpty { return committed }
        return committed + " " + segment
    }

    /// Normalized loudness (0…1) of a capture buffer, for the waveform.
    private static func rmsLevel(_ buffer: AVAudioPCMBuffer) -> CGFloat {
        guard let channel = buffer.floatChannelData?[0] else { return 0 }
        let n = Int(buffer.frameLength)
        guard n > 0 else { return 0 }
        var sum: Float = 0
        for i in 0..<n { let s = channel[i]; sum += s * s }
        let rms = sqrt(sum / Float(n))
        // Speech RMS sits low; scale up generously and clamp so bars clearly react.
        return CGFloat(min(1.0, max(0.0, rms * 18)))
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
