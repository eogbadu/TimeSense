# Skill: Mobile UX — Premium

## Purpose
Keep TimeSense beautiful, simple, premium, and assistant-like. Prevent it from becoming dashboard-heavy, task-manager-first, or cluttered.

## When to Use
- Designing or reviewing any mobile screen
- Creating onboarding flows
- Creating Now / Today / Capture / Insights / Settings screens
- Adding recommendation cards
- Adding empty / error / paywall states
- Adding widgets or notification surfaces
- Reviewing UI for premium quality

## Core UX Philosophy
TimeSense feels like a premium personal assistant. Not a productivity app. Not a dashboard. Not a task manager.

The user should feel:
> "TimeSense understands my real day and helps me make the next good decision."

Not:
> "I have another app to manage."

## Visual Direction
- Apple-like simplicity + subtle futuristic AI feel
- Light mode default
- Premium spacing (generous, breathable)
- Clean typography (SF Pro on iOS, system fonts on Android)
- Soft cards with subtle shadows
- Beautiful, meaningful empty states (not blank screens)
- Smooth animations (60fps, no jank)
- Subtle AI glow/gradient where appropriate
- Haptics where appropriate (iOS Taptic Engine)
- No cluttered productivity dashboard
- No overwhelming analytics wall
- No Notion-like workspace complexity
- No gimmicky sci-fi look

## Content / Copy Rules
- Never guilt-driven: "You're falling behind." ❌
- Always calm and useful: "You have 28 usable minutes before your next event. Best fit: handle one light task." ✓
- "Why this?" is hidden by default — shown only when tapped
- Notifications are helpful, not nagging
- Empty states have meaning and direction

## Interaction Rules
- Cards, buttons, quick taps — not chat-first
- Replans always require approval
- No drag-and-drop schedule editing
- Learning prompts are multiple choice / one tap
- Morning check-in is skippable in one tap
- Evening check-out is one tap

## Screen-Specific Rules

### Now Screen
- Hero card: current context + usable time + best next action
- Quick actions: Done / Snooze / Not Now / Replan / Ask TimeSense / Why this?
- "Why this?" expandable, hidden by default

### Today Screen
- Full vertical timeline: past / current / future
- Past items visually softened
- Current moment clearly highlighted
- No drag-and-drop
- Suggestions shown as cards requiring approval

### Capture Screen
- Voice and text input
- Clean, minimal — one primary action
- Classification shown after capture, not during

### Insights Screen
- Weekly summary only
- No overwhelming analytics
- No endless scrollable metrics
- "What TimeSense learned this week" — friendly, useful, brief

### Settings Screen
- Clear sections
- "What TimeSense Has Learned" — editable, simple list
- No nested-settings-hell

## Files to Read First
- `docs/product/product_brief.md` → UX Principles section
- The CLAUDE.md spec sections 10–14 for detailed UX rules

## Prohibited Actions
- Do not add drag-and-drop schedule editing
- Do not add a Tasks tab or Projects tab to bottom navigation
- Do not add dashboards with multiple metric tiles
- Do not use guilt-driven copy
- Do not make users manually sort, tag, or categorize items as a primary flow
- Do not nag — if a suggestion is ignored, accept it silently

## End-of-Task Requirements
- Screen follows premium visual direction
- All states implemented (loading, empty, error, paywall if applicable)
- No guilt-driven copy
- No cluttered UI
