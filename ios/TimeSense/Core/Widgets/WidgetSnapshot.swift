import Foundation

/// The single contract between the host app and TimeSenseWidgetExtension. The app writes this
/// to the shared App Group container after a successful /now or /timeline/today fetch; the
/// widget extension only ever reads it — it has no network or auth code of its own.
struct WidgetSnapshot: Codable {
    struct Task: Codable {
        let id: String
        let title: String
        let estimatedMinutes: Int?
    }

    struct Event: Codable {
        let title: String
        let start: Date
        let end: Date?
    }

    var usableMinutes: Int
    var bestTask: Task?
    var nextEvent: Event?
    var updatedAt: Date

    static let empty = WidgetSnapshot(usableMinutes: 0, bestTask: nil, nextEvent: nil, updatedAt: .distantPast)

    static let appGroupID = "group.com.timesense.app"
    private static let storageKey = "widget_snapshot_v1"

    static func load() -> WidgetSnapshot? {
        guard let defaults = UserDefaults(suiteName: appGroupID),
              let data = defaults.data(forKey: storageKey) else { return nil }
        return try? JSONDecoder.widgetSnapshot.decode(WidgetSnapshot.self, from: data)
    }

    func save() {
        guard let defaults = UserDefaults(suiteName: Self.appGroupID),
              let data = try? JSONEncoder.widgetSnapshot.encode(self) else { return }
        defaults.set(data, forKey: Self.storageKey)
    }
}

private extension JSONEncoder {
    static let widgetSnapshot: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()
}

private extension JSONDecoder {
    static let widgetSnapshot: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()
}
