# Skill: Native iOS — Swift / SwiftUI

## Purpose
Build the native iOS TimeSense app with SwiftUI and Apple-native integrations. Maintain premium Apple-like UX throughout.

## When to Use
- Creating or modifying any iOS screen
- Building SwiftUI components or views
- Implementing iOS navigation
- Implementing EventKit (Apple Calendar / Reminders)
- Implementing HealthKit
- Implementing App Intents / Siri Shortcuts
- Implementing WidgetKit (home screen / lock screen widgets)
- Implementing Live Activities / Dynamic Island
- Implementing iOS push notifications
- Implementing location permissions
- Implementing StoreKit (in-app purchases)
- Running iOS builds or tests

## Required Inputs
- Active Jira ticket
- Screen or feature to implement
- API endpoints it will consume

## Required Process

1. Read `docs/architecture/architecture_overview.md` → iOS section
2. Follow the feature folder structure: `ios/TimeSense/Features/[FeatureName]/`
3. Use SwiftUI exclusively (no UIKit unless Apple forces it)
4. Use the shared APIClient for backend calls
5. Use shared design tokens for colors, spacing, typography
6. Show loading / empty / error / permission-denied / paywall states on every screen
7. Request permissions with clear explanations before triggering system prompts
8. Never write calendar events without user approval
9. Never enable Focus/DND without user approval
10. Add XCTests for non-trivial logic

## Required Outputs
- SwiftUI View files in `ios/TimeSense/Features/[FeatureName]/`
- Service files in `ios/TimeSense/Services/` (if new service)
- Tests in XCTest target

## Files to Read First
- `docs/architecture/architecture_overview.md`
- `ios/TimeSense/Services/APIClient.swift`
- Design token files

## Commands / Checks
```bash
# Build
xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination "platform=iOS Simulator,name=iPhone 15"

# Test
xcodebuild test -project ios/TimeSense.xcodeproj -scheme TimeSense -destination "platform=iOS Simulator,name=iPhone 15"
```

## Design Rules
- Default: light mode
- Apple-like simplicity + subtle futuristic AI feel
- Premium spacing, clean typography, soft cards
- Smooth animations, haptics where appropriate
- No cluttered productivity dashboard
- No drag-and-drop schedule editor
- No guilt-driven copy
- Empty states must be beautiful, not blank
- "Why this?" hidden by default — only shown when tapped

## Prohibited Actions
- Do not use UIKit unless Apple's framework forces it
- Do not write calendar events without explicit approval UI
- Do not enable DND/Focus without approval
- Do not store user secrets in UserDefaults unencrypted
- Do not make network calls directly from SwiftUI Views — use Services

## End-of-Task Requirements
- App builds without errors
- UI follows premium direction
- Permission flows include explanations
- Project memory updated with iOS notes
