# CRUD to Clinical Maturity Matrix

## Scale

- **L0 - CRUD-only:** data entry/list/edit/delete only
- **L1 - CRUD+:** basic status/filtering/validation
- **L2 - Interactive:** charts, drill-down, workflows, contextual state
- **L3 - Decision-support:** derived interpretation, risk state, triage/escalation guidance

## Matrix

| Domain | Primary Entities | Current Level | Main Gaps | Target Level |
|---|---|---:|---|---:|
| Blood diagnostics | `BloodTest`, `BloodTestInfo`, `MeasurementType`, `Measurement` | L2 | Consistency drift, no unified interpretation layer, limited triage queueing | L3 |
| Vital signs | `VitalSign` | L2 | Weak escalation feedback, no explicit review queue states | L3 |
| Annotation context | `DataPointAnnotation` | L1 | No structured review rationale or decision trace | L2 |
| Import/review workflow | `SourceDocument`, `Measurement` | L2 | Better parser confidence UX, explicit correction provenance | L3 |
| Medication schedules | `MedicationSchedule`, `MedicationLog`, `MedicationInventory`, `PharmacologicalInteraction` | L1-L2 | Need adherence risk timeline, consequence cues, triage states | L3 |
| Alerts and escalation | `CriticalAlert`, `HealthGoal` | L2 | Lifecycle orchestration and ownership not consistently surfaced | L3 |
| Reporting and summaries | `HealthReport`, `IntakeSummary`, `DataExportRequest` | L1-L2 | Inconsistent async feedback and report interpretation detail | L3 |
| Predictive/derived metrics | `BiologicalAgeCalculation`, `PredictiveBiomarker` | L2 | Need explainable snapshots + governance/versioning | L3 |
| Security/privacy/account | `UserProfile`, `SecurityLog`, `UserSession`, `PrivacyPreference`, `ConsentLog`, `AuditLog` | L1 | Stronger clinical-facing trust signals, unified UX language | L2 |
| Sharing and practitioner access | `SecureViewingLink`, `PractitionerAccess`, `StakeholderEmail` | L1 | Workflow guidance and status state clarity | L2 |
| Wearables/integration | `WearableDevice`, `WearableSyncLog`, `IntegrationConfig`, `IntegrationSubTask` | L1-L2 | More resilient sync status UX and task-level interpretation | L2 |
| Lifestyle tracking | `SleepLog`, `CircadianRhythmLog`, `DreamJournal`, `MacronutrientLog`, `MicronutrientLog`, `FoodEntry`, `FastingLog`, `CaffeineAlcoholLog`, `HabitLog`, `Reminder` | L0-L1 | Mostly CRUD, limited clinical linkage and trend interpretation | L2-L3 |
| Physiological logs | `BodyComposition`, `HydrationLog`, `EnergyFatigueLog`, `PainLog`, `RestingMetabolicRate`, `OrthostaticReading`, `ReproductiveHealthLog`, `SymptomJournal`, `MetabolicLog`, `KetoneLog` | L0-L1 | Need summary cards, trajectory, and risk tagging | L2 |

## Prioritized Upgrade Order

1. Blood diagnostics + vitals interpretation consistency (highest patient impact)
2. Import/review confidence and traceability
3. Alerts/reporting/decision-support orchestration
4. Medication adherence and interaction triage
5. Lifestyle and physiological logs promoted from CRUD into insight surfaces
