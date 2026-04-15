# Domain and Clinical Model Specification

## Core Entities

## 1) Patient and Episode Context

- `PatientContext`
  - Role: demographic and baseline reference for interpretation
  - Key fields: age band, sex-at-birth, chronic condition flags, baseline period
- `EncounterEpisode`
  - Role: bind measurements, alerts, and actions into clinically reviewable windows
  - Key fields: start/end timestamps, trigger reason, owner, status

## 2) Measurements and Interpretation

- `MeasurementType` (canonical metric dictionary)
  - name, synonyms, canonical unit, expected-range policy key
- `Measurement` (normalized value event)
  - value, unit, timestamp, source, confidence, review status, patient scope
- `ReferenceRangePolicy`
  - expected min/max by context; policy versioning required
- `TrendAssessment`
  - improving/stable/worsening + slope + window + confidence
- `RiskScoreSnapshot`
  - score, components, interpretation text, model version, computed_at

## 3) Workflow Control Entities

- `Alert`
  - severity, status (new/ack/resolved), trigger source, owner
- `EscalationTask`
  - due-by, assignee, rationale, linked alert/episode
- `ProtocolPlan` / `ProtocolStepEvent`
  - plan definition + adherence events
- `ClinicalNote`
  - clinician rationale and contextual notes linked to events
- `AuditEvent`
  - immutable history of clinically relevant actions

## Derived Clinical States

- `normal`
- `needs_review`
- `high_priority`
- `critical_escalation`

All derived states must include:
- rule provenance
- calculation timestamp
- versioned model/policy key

## Computation Boundaries

- Compute on write:
  - risk snapshots, primary trend state, needs-review flags
- Compute on read:
  - ad hoc analytics and cohort slicing
- Background recompute:
  - stale snapshot refresh and cohort aggregates

## Clinical Workflow Definitions (B4 Closure)

### 1) Intake and Baseline Creation
1. User imports data or enters first measurements.
2. System creates/updates `MeasurementType` mappings and stores normalized `Measurement` rows.
3. System assigns reference policy (`ReferenceRangePolicy`) and computes baseline deltas.
4. Imported rows default to `review_status = pending` until confirmation.
5. Baseline snapshot is marked complete when minimum required core metrics are confirmed.

### 2) Ongoing Monitoring and Follow-Up Review
1. New `Measurement` events are ingested from manual entry, file import, or integration sync.
2. Compute-on-write updates `TrendAssessment` and `RiskScoreSnapshot`.
3. Any state that crosses threshold creates `needs_review` reason metadata.
4. Queue surfaces show pending/deferred measurements ordered by confidence and recency.
5. Reviewer confirms/rejects/defer actions with optional rationale in `confirmation_notes`.

### 3) Alert Triage and Escalation
1. Alert engine evaluates latest data and opens `Alert` records for critical deviations.
2. Triage state progresses from `new` to `acknowledged` to `resolved` (or deferred handling path).
3. High-severity alerts create linked `EscalationTask` with owner and due-by.
4. Resolution action requires explicit operator acknowledgement and audit trace.
5. Unresolved high-priority alerts are re-surfaced in command dashboard priority panel.

### 4) Protocol Adherence and Intervention Tracking
1. Protocol definitions are represented as `ProtocolPlan` and event checkpoints as `ProtocolStepEvent`.
2. Adherence state updates when expected step events are missed, delayed, or completed.
3. Missed adherence can open `needs_review` or linked escalation tasks.
4. Intervention outcomes are captured through follow-up measurements and notes.

### 5) Practitioner Handoff Reporting
1. Reporting window is selected from confirmed measurements and active alerts/tasks.
2. Report assembly includes trend states, expected-range interpretation, and unresolved risks.
3. Export lifecycle records request state (`pending` -> `processing` -> `completed`/`failed`) with timestamps.
4. Generated handoff artifact links evidence to source measurements and decision rationale.
