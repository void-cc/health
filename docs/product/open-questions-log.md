# Open Questions and Decision Log

This log tracks implementation defaults used to unblock roadmap delivery.  
Each default is marked `provisional` until formally approved by product/clinical/legal owners.

## Decision Register (J Closure)

| Domain | Question | Default Decision Used for Build | Status | Owner |
|---|---|---|---|---|
| Technical | Production stack matrix | Python 3.12 + Django 5.x + Postgres + Redis-backed background queue | provisional | Product + DevOps |
| Technical | Cache/worker stack | Use Redis for cache/session primitives and async job orchestration | provisional | DevOps |
| Technical | Observability platform | Structured app logs + request/error counters; retain audit logs >= 1 year | provisional | DevOps |
| Product | Tenancy model | Mixed tenancy: patient self-tracking baseline with clinician review workflows enabled | provisional | Product |
| Product | Backward-compatible screens | Preserve dashboard, blood charts, vitals charts, import/review, and auth/account flows | provisional | Product |
| Product | Rollout strategy | Phase-gated rollout with feature flags and rollback path per slice | provisional | Product |
| Clinical | MVP biomarkers/risk models | Core CBC/lipid/metabolic markers + vitals thresholds; weighted transparent risk state model | provisional | Clinical |
| Clinical | Threshold/copy ownership | Clinical approves thresholds and interpretation vocabulary; FE enforces UI lexicon | provisional | Clinical |
| Clinical | Escalation ownership | Alert lifecycle owned by clinical operations with defined acknowledgment SLA | provisional | Clinical |
| Compliance | Regulatory posture | Treat as PHI-sensitive workflow; enforce least-privilege data access and immutable audit events | provisional | Legal + Product |
| Integration | Phase-1 integrations | Wearables + import pipeline first; FHIR/EHR promoted to phase-2 backlog | provisional | Product |
| Security | Export/share encryption | Require signed access, expiring links, and encrypted-at-rest export storage assumptions | provisional | Security |

## Remaining Approval Actions

1. Convert provisional defaults to approved decisions in governance review.
2. Add approval timestamps and stakeholder sign-off references.
3. Re-run A→J acceptance once approvals are finalized.
