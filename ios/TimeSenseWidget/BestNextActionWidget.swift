import SwiftUI
import WidgetKit

struct BestNextActionWidgetView: View {
    let entry: SnapshotEntry

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("DO NEXT")
                .font(DesignTokens.Typography.caption)
                .foregroundStyle(.secondary)

            if let task = entry.snapshot.bestTask {
                Text(task.title)
                    .font(DesignTokens.Typography.headline)
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                if let minutes = task.estimatedMinutes {
                    Text("~\(minutes) min")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundStyle(.secondary)
                }
            } else {
                Text("All caught up")
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct BestNextActionWidget: Widget {
    let kind = "BestNextActionWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: SnapshotProvider()) { entry in
            BestNextActionWidgetView(entry: entry)
                .containerBackground(.background, for: .widget)
        }
        .configurationDisplayName("Do Next")
        .description("The best task to work on right now.")
        .supportedFamilies([.systemSmall, .accessoryRectangular])
    }
}
