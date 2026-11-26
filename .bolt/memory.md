# Project memory

## Product intent & audience

- AI Virtual Mouse app: controls the OS cursor via hand gestures captured through a webcam.
- Features include pinch-to-click, right-click, pause/resume, two-corner calibration, scroll sensitivity, and usage statistics.
- Audience: end users needing hands-free or gesture-based mouse control.

## Brand personality & voice

- Technical, direct, fix-oriented communication.
- Prefers concise problem → fix explanations over verbose prose.

## Visual design & UX direction

- Multi-page architecture: dashboard, settings, statistics, calibration wizard.
- Dashboard includes an emergency-stop button; layout must avoid conflicting layout systems (grid + absolute on same element caused crashes).
- Settings page uses sliders for scroll sensitivity; changes apply on save.
- Calibration wizard captures two screen corners via pinch gestures.
- Statistics page displays scroll movements and active usage time.
- Error popups used for user-facing failures; ensure all referenced UI components are imported.

## Decisions, constraints & rationale

- Pinch-to-click fires on a single recognized frame rather than requiring N identical frames; gesture filter was silently swallowing clicks. A cooldown still prevents accidental double-clicks.
- Calibration feed: camera loop must pass pinch positions into the wizard; captured area applied immediately and persisted across restarts.
- Statistics tracking: scroll movements and active usage time now counted and surfaced on the Statistics page.
- Scroll sensitivity sliders now write through to scroll behavior on save.
- Project test suite requires a testing library unavailable in the sandbox; behavior verified via equivalent direct checks instead.
- No camera in sandbox; webcam and on-screen behavior require hands-on verification on a real machine.

## Open questions & assumptions

- Full automated test suite cannot run until the required testing library is installed in the dev/CI environment.
- Real webcam performance, lighting robustness, and gesture accuracy remain unverified without hardware access.
- Underlying hand-tracking library and language/framework not yet confirmed from context.