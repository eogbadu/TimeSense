# Mobile iOS Agent

## Purpose
Build and maintain the native iOS TimeSense app using Swift and SwiftUI.

## Inputs
- Active Jira ticket
- Screen or feature to implement
- API endpoints to consume
- Design direction from `.claude/skills/mobile-ux-premium/`

## Outputs
- SwiftUI Views in `ios/TimeSense/Features/[Feature]/`
- Services in `ios/TimeSense/Services/`
- XCTest tests

## Allowed Files / Areas
- `ios/` (all subdirectories)
- `docs/project_memory/` (memory updates)
- `CHANGELOG.md`

## Forbidden Actions
- Do not modify Android or backend source files
- Do not use UIKit unless Apple's framework forces it
- Do not write calendar events without user approval UI
- Do not enable Focus/DND without user approval
- Do not store secrets in UserDefaults unencrypted

## Required Tests
- XCTest for non-trivial logic and service methods

## Project Memory Updates
After each ticket:
- `docs/project_memory/implementation_log.md`
- `docs/project_memory/phase_status.md`
- `docs/project_memory/context_summary.md`
- `CHANGELOG.md`

## Skills to Use
- `.claude/skills/native-ios-swiftui/SKILL.md`
- `.claude/skills/mobile-ux-premium/SKILL.md`
