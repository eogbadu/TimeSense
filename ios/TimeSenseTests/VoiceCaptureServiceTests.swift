import AVFoundation
import XCTest
@testable import TimeSense

/// Tests for voice capture (TIME-314).
///
/// The bug these exist for: on a real iPhone the mic entered the recording state, the waveform
/// appeared, and then nothing — no bar movement, no text — indefinitely and with no error. The
/// engine had "started" successfully; it just never received a buffer. `BUILD SUCCEEDED` said
/// nothing about any of it, and this file had never had a single test.
///
/// The audio graph itself needs hardware, so what is asserted here is the decision logic that used
/// to be missing or wrong: that an unusable input format is REJECTED rather than trusted, and that
/// a permanently failing recognizer is CAPPED rather than restarted forever.
final class VoiceCaptureServiceTests: XCTestCase {

    // MARK: - Input format validation
    //
    // The heart of TIME-314: a 0 Hz / 0 channel format installs a tap without complaint and then
    // delivers silence forever. It must never be accepted.

    func testRejectsZeroSampleRateFormat() {
        let format = AVAudioFormat(streamDescription: &Self.zeroRateDescription)
        // A 0 Hz description may not even construct a format; either outcome is a rejection.
        guard let format else { return }
        XCTAssertFalse(VoiceCaptureService.isUsableInputFormat(format))
    }

    func testRejectsZeroChannelFormat() {
        var description = Self.description(sampleRate: 48_000, channels: 0)
        guard let format = AVAudioFormat(streamDescription: &description) else { return }
        XCTAssertFalse(VoiceCaptureService.isUsableInputFormat(format))
    }

    func testAcceptsNormalHardwareFormat() {
        let format = AVAudioFormat(standardFormatWithSampleRate: 48_000, channels: 1)
        XCTAssertNotNil(format)
        XCTAssertTrue(VoiceCaptureService.isUsableInputFormat(format!))
    }

    // MARK: - Restart cap
    //
    // A pause between sentences legitimately ends a segment, so ordinary dictation restarts often.
    // A recognizer that has genuinely stopped working also "ends a segment" — every time, instantly.
    // The cap has to tell those apart by rate, not by count.

    func testOrdinaryPausesNeverTripTheCap() {
        var history: [Date] = []
        let start = Date()
        // 20 restarts spread a minute apart: a long dictation with many natural pauses.
        for i in 0..<20 {
            let allowed = VoiceCaptureService.allowsRestart(
                now: start.addingTimeInterval(Double(i) * 60),
                history: &history, window: 10, limit: 4
            )
            XCTAssertTrue(allowed, "a pause \(i) minutes in should still be allowed")
        }
    }

    func testRapidFailuresTripTheCap() {
        var history: [Date] = []
        let start = Date()
        var results: [Bool] = []
        // Five restarts inside a second — the signature of a recognizer erroring immediately.
        for i in 0..<5 {
            results.append(VoiceCaptureService.allowsRestart(
                now: start.addingTimeInterval(Double(i) * 0.2),
                history: &history, window: 10, limit: 4
            ))
        }
        XCTAssertEqual(results, [true, true, true, true, false])
    }

    func testCapResetsOnceTheWindowPasses() {
        var history: [Date] = []
        let start = Date()
        for i in 0..<4 {
            _ = VoiceCaptureService.allowsRestart(
                now: start.addingTimeInterval(Double(i) * 0.2),
                history: &history, window: 10, limit: 4
            )
        }
        // Well past the window, the recognizer gets a clean slate rather than staying condemned.
        XCTAssertTrue(VoiceCaptureService.allowsRestart(
            now: start.addingTimeInterval(30), history: &history, window: 10, limit: 4
        ))
    }

    // MARK: - Transcript joining
    //
    // Continuous dictation (TIME-146) depends on this: committed text must survive each new segment.

    func testJoinReturnsSegmentWhenNothingCommitted() {
        XCTAssertEqual(VoiceCaptureService.join("", "call the dentist"), "call the dentist")
    }

    func testJoinKeepsCommittedTextWhenSegmentIsEmpty() {
        XCTAssertEqual(VoiceCaptureService.join("call the dentist", ""), "call the dentist")
    }

    func testJoinSeparatesSegmentsWithASingleSpace() {
        XCTAssertEqual(
            VoiceCaptureService.join("call the dentist", "about Thursday"),
            "call the dentist about Thursday"
        )
    }

    func testJoinOfTwoEmptyStringsIsEmpty() {
        XCTAssertEqual(VoiceCaptureService.join("", ""), "")
    }

    // MARK: - RMS level
    //
    // Drives the waveform. Silence must read 0 — that is exactly what the broken build showed, so
    // these confirm a 0 reading really does mean "no sound", not "no data".

    func testSilenceReadsZero() {
        let buffer = Self.buffer(filledWith: 0)
        XCTAssertEqual(VoiceCaptureService.rmsLevel(buffer), 0, accuracy: 0.0001)
    }

    func testLoudAudioClampsToOne() {
        let buffer = Self.buffer(filledWith: 1.0)
        XCTAssertEqual(VoiceCaptureService.rmsLevel(buffer), 1.0, accuracy: 0.0001)
    }

    func testSpeechLevelAudioLandsBetweenTheExtremes() {
        // ~0.02 RMS is a realistic speaking level. The whole point of TIME-315's curve is that
        // ordinary speech lands in the UPPER half of the range, not bunched just above the floor —
        // under the old linear scale this was 0.36 and the bars barely moved.
        let level = VoiceCaptureService.rmsLevel(Self.buffer(filledWith: 0.02))
        XCTAssertGreaterThan(level, 0.5)
        XCTAssertLessThan(level, 1.0)
    }

    func testQuietSpeechIsStillClearlyVisible() {
        // A soft voice must not read as silence — that ambiguity is what hid TIME-314 for weeks.
        let level = VoiceCaptureService.rmsLevel(Self.buffer(filledWith: 0.005))
        XCTAssertGreaterThan(level, 0.15)
    }

    func testLevelRisesWithLoudness() {
        // Monotonic across the range voices actually occupy.
        let levels = [0.002, 0.005, 0.01, 0.02, 0.03].map {
            VoiceCaptureService.rmsLevel(Self.buffer(filledWith: Float($0)))
        }
        for (quieter, louder) in zip(levels, levels.dropFirst()) {
            XCTAssertLessThan(quieter, louder)
        }
    }

    func testEmptyBufferReadsZero() {
        let buffer = Self.buffer(filledWith: 0.5, frameLength: 0)
        XCTAssertEqual(VoiceCaptureService.rmsLevel(buffer), 0, accuracy: 0.0001)
    }

    // MARK: - Error copy
    //
    // Every one of these was previously either silent or the same catch-all string.

    func testEveryFailureExplainsItself() {
        let cases: [VoiceCaptureError] = [
            .sessionUnavailable, .noAudioInput, .engineFailed, .heardNothing, .recognitionUnavailable
        ]
        for error in cases {
            XCTAssertFalse(error.message.isEmpty, "\(error) must have user-facing copy")
        }
    }

    func testADeadMicrophoneTellsTheUserWhatToDo() {
        // The exact case that shipped broken: it must name the microphone, not say "try again" only.
        XCTAssertTrue(VoiceCaptureError.heardNothing.message.lowercased().contains("microphone"))
        XCTAssertEqual(VoiceCaptureError.noAudioInput.message, VoiceCaptureError.heardNothing.message)
    }

    // MARK: - Helpers

    private static var zeroRateDescription = description(sampleRate: 0, channels: 1)

    private static func description(sampleRate: Double, channels: UInt32) -> AudioStreamBasicDescription {
        AudioStreamBasicDescription(
            mSampleRate: sampleRate,
            mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked,
            mBytesPerPacket: 4 * channels,
            mFramesPerPacket: 1,
            mBytesPerFrame: 4 * channels,
            mChannelsPerFrame: channels,
            mBitsPerChannel: 32,
            mReserved: 0
        )
    }

    private static func buffer(filledWith value: Float, frameLength: AVAudioFrameCount = 1024) -> AVAudioPCMBuffer {
        let format = AVAudioFormat(standardFormatWithSampleRate: 48_000, channels: 1)!
        let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 1024)!
        buffer.frameLength = frameLength
        if let channel = buffer.floatChannelData?[0] {
            for i in 0..<Int(frameLength) { channel[i] = value }
        }
        return buffer
    }
}
