import SwiftUI
import WidgetKit

struct NextEventWidgetView: View {
    let entry: SnapshotEntry

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("NEXT UP")
                .font(DesignTokens.Typography.caption)
                .foregroundStyle(.secondary)

            if let event = entry.snapshot.nextEvent {
                Text(event.title)
                    .font(DesignTokens.Typography.headline)
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                Text(event.start, style: .time)
                    .font(DesignTokens.Typography.footnote)
                    .foregroundStyle(.secondary)
            } else {
                Text("Nothing scheduled")
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct NextEventWidget: Widget {
    let kind = "NextEventWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: SnapshotProvider()) { entry in
            NextEventWidgetView(entry: entry)
                .containerBackground(.background, for: .widget)
        }
        .configurationDisplayName("Next Up")
        .description("Your next scheduled event today.")
        .supportedFamilies([.systemSmall, .accessoryRectangular])
    }
}
