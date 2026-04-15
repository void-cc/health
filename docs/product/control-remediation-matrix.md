# Control Remediation Matrix

## Categories

- `broken`: wired but fails or no-op
- `stub`: visible but behavior missing
- `redundant`: duplicates another action
- `misleading`: label implies behavior not provided

## Matrix

| Control | Category | Decision | Implementation Notes |
|---|---|---|---|
| `#start-tour-btn` | broken | Implement | Wire to guided tour launcher and persist tour completion |
| `#voice-input-btn` | broken | Implement | Align selector in JS and show unsupported fallback |
| Dashboard export buttons | misleading (feedback) | Implement | Add loading, success, failure toasts |
| Chart apply/reset filter buttons | misleading (feedback) | Implement | Add transient loading and disabled state |
| Dead `.dashboard-widget` reorder logic | stub | Remove or implement | Keep only if reorder UX is product requirement |
| Duplicate labels for expected range | misleading | Relabel | Canonicalize wording via copy guide |

## Required Feedback Contract

- Start state: enabled
- Pending: disabled + spinner/progress
- Success: confirmation toast or inline success state
- Failure: explicit error with retry action
