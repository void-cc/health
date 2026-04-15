# Lean Quality and Safety Plan

## Goal

Reduce test runtime substantially while preserving high-value clinical safety coverage.

## Test Lane Strategy

## Fast PR Lane (blocking)
- Migration graph check
- Focused unit tests:
  - expected-range classification
  - risk/trend calculations
  - unit conversion safety
- Focused integration tests:
  - import -> review -> queue update
  - measurement update -> alert transition
  - export request -> generation -> download state
- Minimal smoke UI checks:
  - login and dashboard load
  - one chart filter action
  - one async feedback action

Target runtime: <=10 minutes.

## Nightly Lane (non-blocking initially)
- Extended integration coverage
- Additional UI flows and browser matrix
- Optional visual/snapshot checks

## Safety Controls

- Audit trail required for clinically relevant writes.
- Replace silent exception paths with structured logs + user feedback.
- Explicit unknown-state handling for missing values.
- Outlier detection path must distinguish likely input error from critical clinical event.
