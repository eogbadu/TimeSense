# App Store Screenshots

Marketing screenshots for the App Store listing — real app screens (cosmic theme, domain-coloured
recommendations) composed onto a cosmic backdrop with a Didot serif headline.

## Files (1290 × 2796 — iPhone 6.7")

| # | File | Screen | Headline |
|---|------|--------|----------|
| 1 | `01_now_focus.png`  | Now — deep-work recommendation (blue) | Know the best next step |
| 2 | `02_now_health.png` | Now — walk recommendation (green)     | Work with your energy |
| 3 | `03_capture.png`    | Capture (voice orb)                   | Just say it. |
| 4 | `04_why.png`        | Why this recommendation (signals)     | Understand every call |
| 5 | `05_insights.png`   | Insights                              | Plan, reflect, improve |

## Sizes

- Rendered at **1290 × 2796** (iPhone 6.7" — 14/15 Pro Max), accepted by App Store Connect for the
  6.5"/6.7" slots.
- For the 6.9" slot (iPhone 16 Pro Max), regenerate at **1320 × 2868** by changing `W, H` in
  `build_screenshots.py`.

## Regenerating

The app screens are captured from the simulator using a DEBUG-only env-driven mock (`MOCK_NOW`,
`MOCK_TITLE`, `MOCK_TAB`, `MOCK_WHY`) — see the PR for the temporary harness (reverted after capture).
Then `build_screenshots.py` (Pillow) composes each capture onto the cosmic backdrop with the headline.

Fonts: Didot (headline/wordmark), Helvetica (subtitle) — both system fonts on macOS.
