import SwiftUI

struct TimelineCard: View {
    let task: TimelineTask
    let visualState: TimelineVisualState

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            timeColumn
            Divider()
                .frame(height: 48)
                .overlay(dividerColor)
            contentColumn
        }
        .padding(DesignTokens.Spacing.md)
        .background(backgroundColor)
        .cornerRadius(DesignTokens.Radius.md)
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
                .stroke(borderColor, lineWidth: visualState == .current ? 2 : 0)
        )
        .opacity(visualState == .past ? 0.5 : 1.0)
    }

    private var timeColumn: some View {
        VStack(alignment: .trailing, spacing: 2) {
            if let start = task.scheduledStart {
                Text(start, format: .dateTime.hour().minute())
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(timeColor)
                    .monospacedDigit()
            }
            if let end = task.scheduledEnd {
                Text(end, format: .dateTime.hour().minute())
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .monospacedDigit()
            }
        }
        .frame(width: 52, alignment: .trailing)
    }

    private var contentColumn: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(task.title)
                .font(DesignTokens.Typography.body)
                .foregroundColor(visualState == .past ? DesignTokens.Color.textSecondary : DesignTokens.Color.textPrimary)
                .strikethrough(task.status == "done")
                .lineLimit(2)
            if let mins = task.estimatedMinutes {
                Text("\(mins) min")
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var backgroundColor: Color {
        switch visualState {
        case .current: return DesignTokens.Color.accent.opacity(0.08)
        default:       return DesignTokens.Color.surface
        }
    }

    private var dividerColor: Color {
        switch visualState {
        case .current: return DesignTokens.Color.accent
        case .past:    return DesignTokens.Color.textSecondary.opacity(0.3)
        case .done:    return DesignTokens.Color.textSecondary.opacity(0.3)
        case .future:  return DesignTokens.Color.accent.opacity(0.4)
        }
    }

    private var borderColor: Color {
        visualState == .current ? DesignTokens.Color.accent : .clear
    }

    private var timeColor: Color {
        visualState == .current ? DesignTokens.Color.accent : DesignTokens.Color.textPrimary
    }
}
