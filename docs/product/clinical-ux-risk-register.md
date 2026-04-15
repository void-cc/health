# Clinical UX Risk Register

## Severity Scale

- **P0**: Critical patient-safety or severe trust risk
- **P1**: High-impact clinical usability/trust risk
- **P2**: Moderate workflow inefficiency or cognitive burden
- **P3**: Low-impact polish or discoverability issue

## Active Risks

| ID | Severity | Risk | Evidence | Mitigation |
|---|---|---|---|---|
| R-001 | P1 | Embedded chart labels drift from canonical copy system | `templates/index.html` uses mixed “Range” phrasing in embedded charts while detail pages use “Expected range” | Normalize all embedded labels and maintain single lexicon reference |
| R-002 | P1 | Auth/dashboard visual mismatch undermines product trust continuity | `static/css/auth.css` still contains legacy animated gradient/glass style blocks | Enforce clinical-calm auth theme tokens and remove obsolete style path |
| R-003 | P2 | Dashboard action density increases cognitive load | Header actions + quick actions + per-row actions compete in main view | Further progressive disclosure and task-priority hierarchy |
| R-004 | P2 | Async failures are too silent for key operations | Export and chart interactions lack consistent success/error feedback | Introduce unified async feedback pattern and retry affordances |
| R-005 | P3 | Abbreviation comprehension friction for first-time users | BBT/SpO2 labels appear without contextual explanation in key views | Add first-use inline glossary hints/tooltips |
| R-006 | P2 | CSS/JS duplication increases future drift risk | Repeated chart selectors in `static/css/saas.css`, duplicate chart/export script logic in templates | Centralize shared styles and reusable chart/export utilities |
| R-007 | P1 | Potential interaction dead paths reduce reliability | Tour button and voice selector mismatch between template and JS | Resolve wiring mismatches and add smoke tests for control wiring |

## Acceptance Criteria for Risk Closure

- **R-001 closed** when all analytics surfaces use one approved terminology set.
- **R-002 closed** when auth and app surfaces share one tokenized visual language.
- **R-003 closed** when decision points expose <=4 primary choices by default.
- **R-004 closed** when all high-impact async actions provide loading + success/error feedback.
- **R-005 closed** when first-use users can access concise definitions without leaving context.
- **R-006 closed** when duplicated chart style/script blocks are consolidated.
- **R-007 closed** when all high-priority controls have passing behavior checks.
