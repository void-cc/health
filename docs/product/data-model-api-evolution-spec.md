# Data Model and API Evolution Spec

## Data Model Evolution

## 1) Tenancy and Scoping

- Enforce explicit patient/user ownership on all records used in review and analytics.
- Remove ambiguous global-query behavior from clinical workflows.

## 2) Validation and Constraints

- Physiological bounds by measurement type.
- Unit compatibility and conversion checks.
- Required fields for clinically meaningful interpretation.
- State transition guards for review and alert lifecycles.

## 3) Derived Persistence

Persist and version:
- `risk_score_snapshot`
- `trend_assessment`
- `needs_review_reason`
- `last_reviewed_at`

## API Contract Families

## A) Raw Data APIs
- Purpose: CRUD and source-level retrieval
- Must include pagination and sorting

## B) Summary APIs
- Purpose: dashboard cards and trend summaries
- Must include freshness metadata and interpretation confidence

## C) Triage APIs
- Purpose: review queues and escalation actions
- Must include severity, ownership, due-by, and action state

## Query Standard

All list/summary APIs support:
- `date_from`, `date_to`
- `severity`
- `status`
- `needs_review`
- `page`, `page_size`, `sort`
