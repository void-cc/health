# UX and Interaction Redesign Specification

## Dashboard Architecture

## A) Command Dashboard (triage-first)
- First panel: items requiring review now
- Second panel: unresolved alerts and overdue protocol steps
- Third panel: recent trend changes requiring clinician attention

## B) Patient Detail Workspace
- Unified timeline of biomarkers, vitals, symptoms, medications
- Left rail: key status and trend summary
- Main pane: charts and event overlays
- Right pane: notes, tasks, and recommendations

## C) Cohort Analytics
- Risk distribution and trend drift by segment
- Outlier and adherence cohort filters
- Drilldown to patient-level evidence

## Visualization Standards

- Expected range band is mandatory for relevant biomarkers.
- Critical threshold crossings are visually distinct.
- Time-range presets: 7d, 30d, 90d, 1y, all.
- Hover tooltip contains:
  - raw value
  - expected range
  - trend state
  - contextual event notes if present

## Interaction Standards

- Decision point default should expose <=4 high-priority options.
- Advanced actions must be tucked behind progressive disclosure.
- All async controls require loading, success, and error states.

## Critique-Driven UX Rules

1. Embedded chart labels must use canonical terminology from copy guide.
2. Auth and app pages must share one visual language.
3. Action density is intentionally reduced on primary workflow screens.
4. First-time abbreviation help appears inline (BBT, SpO2, etc.).

## End-to-End Interaction Workflows (B4 Closure)

### Intake to Review
1. Import or manual entry lands measurements in a pending-review queue.
2. Reviewer opens measurement detail, checks source confidence, and selects confirm/reject/defer.
3. Confirmed entries immediately update dashboard summaries and trend cards.

### Triage to Escalation
1. Command dashboard highlights `needs_review` and high-priority alerts.
2. Selecting an alert opens supporting evidence (chart + recent events + notes).
3. User can acknowledge, resolve, or escalate with explicit feedback and audit logging.

### Follow-Up and Reporting
1. Patient workspace tracks resolution progress and follow-up data freshness.
2. Practitioner report flow pulls confirmed measurements, trend states, and open risks.
3. Export flow surfaces pending/progress/failure states before download.
