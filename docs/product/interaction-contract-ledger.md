# Interaction Contract Ledger

This ledger enumerates high-impact controls and required behavior contracts.

## Status Categories

- `working`
- `broken`
- `stub`
- `redundant`
- `misleading`

## High-Impact Controls

| Surface | Control | Current Status | Required Contract |
|---|---|---|---|
| `templates/base.html` | `#start-tour-btn` | broken | Wire to guided-tour launcher with clear start/resume state and completion feedback |
| `templates/base.html` + `static/js/ui.js` | `#voice-input-btn` | broken | Align selector and handler; show unsupported-state notice when API unavailable |
| `templates/index.html` | Dashboard Export PDF | working (weak feedback) | Add loading state, success toast, failure toast with retry |
| `templates/blood_charts.html` | Apply filter / Reset filters | working (weak feedback) | Disable buttons during redraw; show transient progress and empty-result guidance |
| `templates/vitals_charts.html` | Apply filter / Reset filters | working (weak feedback) | Same as blood charts contract |
| `templates/comparative_bar_charts.html` | Export PDF | working (weak feedback) | Async state and explicit error messaging |
| `templates/index.html` | Quick actions expansion (`details`) | working | Keep progressive disclosure default-collapsed; highlight only if onboarding tip active |
| `templates/index.html` | Keyboard shortcuts modal opener | working | Preserve discoverability and include “replay onboarding tips” link |
| `templates/index.html` | Per-result menu actions | working | Standardize action labels + confirmation UX + refresh behavior |
| `templates/index.html` | Result filter pills | working | Keep active-state visibility and `aria-live` result count updates |
| `static/js/ui.js` | Widget drag/reorder handler (`.dashboard-widget`) | stub | Either implement on real widgets or remove dead branch |

## Decision Matrix

| Category | Action |
|---|---|
| broken | Implement now with full async/feedback contract |
| stub | Implement only if clinically valuable; otherwise remove |
| redundant | Merge into single canonical control |
| misleading | Relabel or replace with explicit action |

## Required Async Feedback Contract (All Retained Actions)

1. Disable control while request is in progress.
2. Show inline/loading indicator if action takes >250ms.
3. Show success confirmation for user-visible operations.
4. Show contextual error with retry for failures.
5. Log action outcome for audit/diagnostic visibility.
