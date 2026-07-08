import AVFoundation
import Foundation
import Speech

/// On-device speech-to-text for the Capture screen. Transcribes the microphone into text (live
/// partial results), keeping recognition on-device where supported. We never persist or upload raw
/// audio — only the transcript, which flows into the normal capture pipeline.
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
        transcript = ""
        do {
            try beginRecording(with: recognizer)
            isRecording = true
        } catch {
            errorMessage = "Couldn't start recording."
            cleanup()
        }
    }

    func stop() {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        request?.endAudio()
        isRecording = false
        level = 0
    }

    private func beginRecording(with recognizer: SFSpeechRecognizer) throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: .duckOthers)
        try session.setActive(true, options: .notifyOthersOnDeactivation)

        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        if recognizer.supportsOnDeviceRecognition {
            req.requiresOnDeviceRecognition = true   // keep audio on-device (privacy)
        }
        request = req

        let input = audioEngine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            self?.request?.append(buffer)
            let lvl = Self.rmsLevel(buffer)
            Task { @MainActor in self?.level = lvl }
        }
        audioEngine.prepare()
        try audioEngine.start()

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            Task { @MainActor in
                guard let self else { return }
                if let result {
                    self.transcript = result.bestTranscription.formattedString
                    if result.isFinal { self.cleanup() }
                }
                if error != nil { self.cleanup() }
            }
        }
    }

    private func cleanup() {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        task?.cancel()
        request = nil
        task = nil
        isRecording = false
        level = 0
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    /// Normalized loudness (0…1) of a capture buffer, for the waveform.
    private static func rmsLevel(_ buffer: AVAudioPCMBuffer) -> CGFloat {
        guard let channel = buffer.floatChannelData?[0] else { return 0 }
        let n = Int(buffer.frameLength)
        guard n > 0 else { return 0 }
        var sum: Float = 0
        for i in 0..<n { let s = channel[i]; sum += s * s }
        let rms = sqrt(sum / Float(n))
        // Speech RMS sits around 0…0.2; scale up with headroom and clamp.
        return CGFloat(min(1.0, max(0.0, rms * 12)))
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
