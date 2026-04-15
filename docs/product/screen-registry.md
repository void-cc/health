# Screen Registry

This registry maps the current application surface to screen purpose and implementation state.

## Inventory Method

- Source of truth for routes: `tracker/urls.py`
- Source of truth for rendering and behavior: `tracker/views.py`, `tracker/auth_views.py`, `templates/*`, `static/js/ui.js`
- Classification dimensions:
  - Screen type: dashboard, list, detail, form, chart, workflow, settings, account/security, API
  - Workflow domain: diagnostics, vitals, medications, imports, interoperability, notifications, lifestyle
  - Maturity:
    - `CRUD-only`
    - `CRUD+` (basic filtering/status)
    - `Interactive` (multi-step interactions, chart/filter/drilldown)
    - `Decision-support` (derived interpretation, triage, or recommendation)

## High-Level Route Map

## 1) Core Diagnostics and Dashboard

| Route | Screen | Type | Purpose | Current Behavior | Maturity |
|---|---|---|---|---|---|
| `/` | `templates/index.html` | Dashboard | Primary patient overview | KPI cards, result filters, embedded charts, shortcuts, export | Interactive |
| `/history/` | `templates/history.html` | List/Timeline | Historical blood test review | Table/list with chart links | CRUD+ |
| `/vitals/` | `templates/vitals.html` | List | Vital signs history | List and CRUD actions | CRUD+ |
| `/chart/<test_name>/` | `templates/chart.html` | Detail + Chart | Single test trend | Trend chart + annotation table | Interactive |
| `/blood_tests/charts/` | `templates/blood_charts.html` | Analytics | Multi-marker blood trends | Date filter, MA toggle, anomaly toggle, export | Interactive |
| `/blood_tests/boxplots/` | `templates/blood_boxplots.html` | Analytics | Distribution analysis | Boxplot chart cards + export | Interactive |
| `/blood_tests/bar_charts/` | `templates/comparative_bar_charts.html` | Analytics | Compare against expected ranges | Comparative bars + status badges + export | Interactive |
| `/vitals/charts/` | `templates/vitals_charts.html` | Analytics | Vitals trends | Date filter, MA toggle, anomaly toggle, export | Interactive |
| `/scatter/` | `templates/scatter_plots.html` | Analytics | Correlation exploration | Metric selectors + scatter chart | Interactive |

## 2) Intake, Import, and Review

| Route | Screen | Type | Purpose | Current Behavior | Maturity |
|---|---|---|---|---|---|
| `/import/` | `templates/import_data.html` | Form/Workflow | Import external data | CSV/PDF/HL7/FHIR ingestion entrypoint | Interactive |
| `/measurements/review/` | `templates/review_measurements.html` | Workflow Queue | Confirm/reject parsed measurements | Status-driven review actions | Decision-support |
| `/imports/<doc_id>/review/` | `templates/review_import.html` | Workflow Detail | Review specific import batch | Batch review and resolve | Decision-support |
| `/measurements/staff-edit/<pk>/` | `templates/staff_edit_measurement.html` | Form | Elevated correction path | Staff override edit | CRUD+ |
| `/measurements/staff-delete/<pk>/` | `templates/staff_delete_measurement.html` | Confirm | Elevated delete path | Staff confirm deletion | CRUD+ |

## 3) Medications and Interactions

| Route Group | Type | Purpose | Current Behavior | Maturity |
|---|---|---|---|---|
| `/medications/*` | CRUD + detail | Schedule, dosing, concept lookup | CRUD plus autocomplete/detail | CRUD+ |
| `/medications/log/*` | CRUD | Dose event log | Standard list/add/edit/delete | CRUD-only |
| `/medications/inventory/*` | CRUD | Inventory tracking | Standard CRUD | CRUD-only |
| `/interactions/*` | CRUD + dashboard | Interaction reference and review | CRUD plus dashboard | Interactive |

## 4) Lifestyle and Tracking Modules

| Route Group | Domain | Current Behavior | Maturity |
|---|---|---|---|
| `/sleep/*`, `/sleep/dashboard/` | Sleep | CRUD + dashboard summaries | CRUD+ |
| `/nutrition/dashboard/` | Nutrition | Aggregate dashboard | Interactive |
| `/circadian/*`, `/dreams/*` | Sleep context | Mostly list/forms | CRUD-only |
| `/macros/*`, `/micros/*`, `/food/*`, `/fasting/*`, `/caffeine-alcohol/*` | Nutrition/metabolic | Primarily CRUD | CRUD-only |
| `/pain/*`, `/energy/*`, `/hydration/*`, `/metabolic/*`, `/ketones/*`, `/rmr/*`, `/orthostatic/*`, `/reproductive/*`, `/symptoms/*` | Physiological logs | Standard CRUD | CRUD-only |

## 5) Security, Access, and Sharing

| Route Group | Type | Purpose | Current Behavior | Maturity |
|---|---|---|---|---|
| `/accounts/*` | Account/security | Login, profile, sessions, MFA, privacy | Functional but visual mismatch with main app | CRUD+ |
| `/secure-links/*`, `/share/<token>/` | Sharing | Secure external view links | CRUD + tokenized access | CRUD+ |
| `/practitioners/*`, `/practitioner-portal/*` | Access workflow | Practitioner access management | CRUD+ |

## 6) Reporting, Alerts, and Decision Surfaces

| Route Group | Purpose | Current Behavior | Maturity |
|---|---|---|---|
| `/alerts/*`, `/alerts/auto-check/` | Alerting | CRUD + automated check action | Decision-support |
| `/reports/*`, `/reports/generate/` | Report generation | CRUD + generate action | Interactive |
| `/bio-age/*`, `/bio-age/estimate/` | Derived estimate | CRUD + estimate action | Decision-support |
| `/biomarkers/*`, `/biomarkers/generate/` | Predictive markers | CRUD + generation action | Decision-support |
| `/timeline/`, `/labs/` | Longitudinal + lab analytics | Aggregated review surfaces | Interactive |

## 7) Interop, Integrations, Notifications

| Route Group | Purpose | Current Behavior | Maturity |
|---|---|---|---|
| `/wearables/*` | Device integration and sync | CRUD + connect/sync/callback/logs | Interactive |
| `/integrations/*`, `/subtasks/*`, `/phase11/` | Integration config and implementation dashboard | CRUD + status dashboard | CRUD+ |
| `/notifications/*` | Notification templates/triggers/logs/preferences | CRUD + channel assignment | CRUD+ |
| `/exports/*` | Export request and download | CRUD + generated download | Interactive |

## Known Surface-Level Gaps to Resolve in Implementation

- Dashboard and chart-copy consistency drift (range terminology/casing) remains in embedded chart blocks.
- Some UI controls are visually present but not reliably wired (tour button, voice button selector mismatch).
- High action density on main dashboard creates cognitive overhead.
- Async feedback is inconsistent across export/filter actions.
