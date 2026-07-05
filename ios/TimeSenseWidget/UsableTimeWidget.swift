import SwiftUI
import WidgetKit

struct UsableTimeWidgetView: View {
    let entry: SnapshotEntry

    private var hasSynced: Bool { entry.snapshot.updatedAt != .distantPast }

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("USABLE TIME")
                .font(DesignTokens.Typography.caption)
                .foregroundStyle(.secondary)

            if hasSynced {
                Text(formattedMinutes(entry.snapshot.usableMinutes))
                    .font(DesignTokens.Typography.title)
                    .foregroundStyle(.primary)
                Text("left today")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundStyle(.secondary)
            } else {
                Text("Open TimeSense")
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func formattedMinutes(_ minutes: Int) -> String {
        guard minutes > 0 else { return "0m" }
        let hours = minutes / 60
        let mins = minutes % 60
        if hours == 0 { return "\(mins)m" }
        if mins == 0 { return "\(hours)h" }
        return "\(hours)h \(mins)m"
    }
}

struct UsableTimeWidget: Widget {
    let kind = "UsableTimeWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: SnapshotProvider()) { entry in
            UsableTimeWidgetView(entry: entry)
                .containerBackground(.background, for: .widget)
        }
        .configurationDisplayName("Usable Time")
        .description("How much focus time you have left today.")
        .supportedFamilies([.systemSmall, .accessoryRectangular])
    }
}
