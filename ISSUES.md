# Known Issues & Placeholder Features

This document is a complete audit of features that are either placeholder
implementations, unreachable through the UI, incorrectly implemented, or that
have a significant design gap between what they claim to do and what they
actually do.

---

## 1. Authentication & Access Control

### 1.1 — 53 view functions are not protected by `@login_required`

**Affected files:** `tracker/views.py`

The following categories of views are missing the `@login_required` decorator,
meaning any unauthenticated visitor can access or mutate sensitive health data:

- All Wearable Device views (`wearable_device_list`, `wearable_device_add`,
  `wearable_device_edit`, `wearable_device_delete`, `wearable_device_sync`,
  `sync_log_list`)
- All Administration views (`user_profile_*`, `family_account_*`,
  `consent_log_*`, `tenant_config_*`, `admin_telemetry_*`, `api_rate_limit_*`,
  `encryption_key_*`, `audit_log_*`, `anonymized_data_*`,
  `database_scaling_*`, `backup_config_*`)
- Most Intelligence/Analytics views (`medication_schedule_*`, `health_goal_*`,
  `critical_alert_*`, `critical_alert_auto_check`, `health_report_*`,
  `health_report_generate`, `biological_age_*`, `biological_age_estimate`,
  `predictive_biomarker_*`, `predictive_biomarker_generate`)
- Sharing views (`secure_viewing_link_add`, `secure_viewing_link_edit`,
  `practitioner_portal`, `practitioner_request_access`, `intake_summary_*`,
  `intake_summary_generate`, `data_export_*`, `data_export_download`,
  `data_export_add`, `stakeholder_email_*`, `stakeholder_email_send`)
- Integration views (`integration_config_activate`,
  `phase11_dashboard`, `practitioner_access_edit`)

### 1.2 — RBAC roles are stored but never enforced

**Affected files:** `tracker/models.py` (`UserProfile`), `tracker/views.py`

`UserProfile.role` has three values (`admin`, `user`, `practitioner`) but
nowhere in the application is this field read to restrict or grant access to
any view or action. Any logged-in user can reach any page regardless of role.

### 1.3 — Admin user-management pages are accessible by all users

**Affected files:** `tracker/views.py`, `tracker/urls.py`

Pages under the **Administration** sidebar section (User Profiles, Family
Accounts, Consent Logs, etc.) have no admin-only guard. Any
authenticated user can view, create, edit, or delete other users' profiles and
system-wide configurations.

---

## 2. No Multi-User Data Isolation

### 2.1 — All health data is global, not scoped to the logged-in user

**Affected files:** `tracker/models.py`, `tracker/views.py`

The core health data models (`BloodTest`, `VitalSign`, `BodyComposition`,
`HydrationLog`, `SleepLog`, `MetabolicLog`, etc.) have no `user` or
`owner` foreign key. Every query uses `Model.objects.all()` without
filtering by `request.user`, so all users share one data pool. Adding a
blood test as User A makes it visible to User B.

### 2.2 — Secure Viewing Links expose all users' data

**Affected files:** `tracker/views.py` (`secure_link_shared_view`)

When a secure link is followed, `BloodTest.objects.all()`,
`VitalSign.objects.all()`, and `MedicationSchedule.objects.all()` are
returned with no user filter. In a multi-user deployment any shareable link
leaks every user's data to the recipient.

### 2.3 — Practitioner Portal exposes all users' data

**Affected files:** `tracker/views.py` (`practitioner_portal`)

After a practitioner's email is validated, the same unscoped `.all()` queries
are used to build the patient data shown to the practitioner, regardless of
which patient actually granted the access.

---

## 3. Missing or Unreachable Features

### 3.1 — ~~`ClinicalTrialMatch` model has no views, URLs, or UI at all~~ **RESOLVED — model removed**

### 3.2 — `PharmacologicalInteraction` model has no views, URLs, or UI at all

**Affected files:** `tracker/models.py`, `tracker/views.py`, `tracker/urls.py`

Same situation as `ClinicalTrialMatch`. The model is defined and imported but
there is no way to view, create, edit, or delete interactions through the UI.
No drug-interaction checking is wired up to the Medications feature either.

---

## 4. Placeholder / Stub Implementations

### 4.1 — ~~`WearableDevice.trigger_sync()` creates empty placeholder records~~ **RESOLVED — fake data creation removed; now returns an error until a real integration client is wired up**

### 4.2 — ~~`IntegrationConfig.run_integration()` does nothing~~ **RESOLVED — stub method removed**

### 4.3 — `DataExportRequest` supports CSV and PDF formats that are never generated

**Affected files:** `tracker/models.py` (`FORMAT_CHOICES`), `tracker/views.py`
(`data_export_download`)

`FORMAT_CHOICES` lists four formats: JSON, XML, CSV, PDF. The
`data_export_download` view only handles `xml` and falls back to JSON for
everything else. Selecting CSV or PDF produces a JSON file with a `.json`
extension.

### 4.4 — ~~`APIRateLimitConfig` settings are stored but rate limiting is never enforced~~ **RESOLVED — model removed**

### 4.5 — ~~`EncryptionKey` stores public keys but data is never encrypted~~ **RESOLVED — model removed**

### 4.6 — ~~`BackupConfiguration` has no scheduler or execution logic~~ **RESOLVED — model removed**

### 4.7 — ~~`DatabaseScalingConfig` has no effect on the database~~ **RESOLVED — model removed**

### 4.8 — ~~`AdminTelemetry` requires manual data entry~~ **RESOLVED — model removed**

---

## 5. Broken Form / View Logic

### 5.1 — `FamilyAccount` add/edit passes a string instead of a `UserProfile` FK

**Affected files:** `tracker/views.py` (`family_account_add`,
`family_account_edit`)

The view assigns `primary_user=request.POST.get('primary_user', '')`, passing
a raw string to a `ForeignKey` field. This will raise an exception on save.
Additionally the template iterates over `{% for value, label in profiles %}`
but the view never passes a `profiles` context variable, causing a template
rendering error on GET requests.

### 5.2 — `SecureViewingLink.expires_at` is non-nullable but can be omitted at creation

**Affected files:** `tracker/models.py` (line 1468), `tracker/views.py`
(`secure_viewing_link_add`)

`expires_at = models.DateTimeField()` is non-nullable. The add view sets
`expires_dt = None` when no date is submitted and then calls
`SecureViewingLink.objects.create(..., expires_at=None)`. This raises an
`IntegrityError` that is silently caught and presented to the user as a
generic "Error creating secure viewing link."

### 5.3 — `intake_summary_generate` executes on GET requests

**Affected files:** `tracker/views.py` (`intake_summary_generate`)

The view has no `if request.method == 'POST':` guard. Visiting the URL
directly (e.g. clicking the "Auto-Generate" link, which uses an `<a href>` not
a form POST) immediately creates a new `IntakeSummary` record. Every page
visit, browser pre-fetch, or link preview creates duplicate entries.

### 5.4 — New users created via the admin User Profile form cannot log in

**Affected files:** `tracker/views.py` (`user_profile_add`)

The view calls `user.set_unusable_password()` on every new user, which
permanently prevents password-based authentication. These accounts are
unreachable until an admin manually resets the password.

### 5.5 — `health_report_list.html` shows the raw `report_type` code

**Affected files:** `templates/health_report_list.html`

The template uses `{{ entry.report_type }}` which renders `monthly` / `quarterly`
/ `annual` instead of `{{ entry.get_report_type_display }}` which would show
"Monthly Summary" / "Quarterly Review" / "Annual Report".

### 5.6 — `critical_alert_list.html` shows the raw `alert_level` code

**Affected files:** `templates/critical_alert_list.html`

The same issue: `{{ entry.alert_level }}` renders `warning` / `critical` /
`emergency` instead of the human-readable label from `ALERT_LEVELS`.

---

## 6. UI / Template Issues

### 6.1 — `practitioner_portal.html` does not extend `base.html`

**Affected files:** `templates/practitioner_portal.html`

This template is a standalone HTML page that loads Bootstrap from a CDN and
has its own `<html>`, `<head>`, and `<body>`. It does not extend `base.html`,
so it has no sidebar navigation, no top navbar, no dark-mode support, and no
consistent styling with the rest of the application. Users who land on this
page have no way to navigate back except using the browser's back button.

### 6.2 — `UserProfile.theme_preference` is editable but never applied server-side

**Affected files:** `tracker/models.py`, `tracker/auth_views.py`,
`templates/base.html`

The profile form lets users set a theme preference (`light`, `dark`,
`system`). This value is saved to the database but is never read back. The
actual dark-mode implementation is entirely `localStorage`-based in
`static/js/ui.js`. The saved preference is ignored on every page load.

### 6.3 — `AuditLog` is exposed as a fully editable CRUD interface

**Affected files:** `tracker/views.py`, `tracker/urls.py`,
`templates/audit_log_*.html`

Audit logs are a security record and should be append-only. The current
implementation provides add, edit, and delete routes for audit log entries,
allowing any user (or unauthenticated visitor, per issue 1.1) to forge,
modify, or erase the audit trail.

---

## 7. Summary Table

| # | Area | Issue | Severity |
|---|------|-------|----------|
| 1.1 | Auth | 53 views missing `@login_required` | Critical |
| 1.2 | Auth | RBAC roles stored but never enforced | High |
| 1.3 | Auth | Admin pages accessible by all users | High |
| 2.1 | Data | No per-user data isolation on any model | High |
| 2.2 | Data | Secure links expose all users' data | High |
| 2.3 | Data | Practitioner portal exposes all users' data | High |
| 3.1 | Missing | `ClinicalTrialMatch` has no UI | Medium |
| 3.2 | Missing | `PharmacologicalInteraction` has no UI | Medium |
| 4.1 | Stub | Wearable `trigger_sync` creates empty placeholder records | Medium |
| 4.2 | Stub | `IntegrationConfig.run_integration()` does nothing | Medium |
| 4.3 | Stub | CSV and PDF export formats produce JSON output | Medium |
| 4.4 | Stub | `APIRateLimitConfig` has no enforcement | Medium |
| 4.5 | Stub | `EncryptionKey` never used to encrypt data | Medium |
| 4.6 | Stub | `BackupConfiguration` has no execution mechanism | Low |
| 4.7 | Stub | `DatabaseScalingConfig` has no effect | Low |
| 4.8 | Stub | `AdminTelemetry` requires manual entry | Low |
| 5.1 | Bug | `FamilyAccount` form passes string instead of FK | High |
| 5.2 | Bug | `SecureViewingLink` creation fails silently with no expiry | Medium |
| 5.3 | Bug | `intake_summary_generate` fires on GET, creates duplicates | Medium |
| 5.4 | Bug | Admin-created users cannot log in (`set_unusable_password`) | High |
| 5.5 | UI | Health report list shows raw `report_type` code | Low |
| 5.6 | UI | Critical alert list shows raw `alert_level` code | Low |
| 6.1 | UI | Practitioner portal does not extend `base.html` | Medium |
| 6.2 | UI | `theme_preference` saved but never applied | Low |
| 6.3 | Security | `AuditLog` is fully editable/deletable | High |
| 8.1 | Bug | HL7 parsing swallows `ValueError` | Medium |
| 8.2 | Bug | FHIR JSON parsing is brittle | High |
| 8.3 | Bug | CSV Importer `Exception` block hides errors | High |
| 8.4 | Bug | OCR parsing fails on multi-page PDFs | High |
| 9.1 | Stub | Wearable APIs are entirely mocked | Medium |
| 9.2 | Stub | `IntegrationSubTask` doesn't trigger workflows | Medium |
| 9.3 | Security | OAuth credentials stored in plaintext | Critical |
| 9.4 | Bug | Telehealth links expire but no background cleanup | Low |
| 10.1 | Bug | Critical Alerts trigger infinitely | Medium |
| 10.2 | Security | Notification templates lack escaping | High |
| 10.3 | Perf | Email delivery is synchronous | Medium |
| 10.4 | Stub | Push notifications lack a provider | Low |
| 11.1 | Bug | Broken test suite due to syntax error | High |
| 11.2 | Bug | Migrations fail on conflicting leaf nodes | Critical |
| 11.3 | Bug | Migrations fail on `patient_id` duplicate column | Critical |
| 11.4 | Tests | Coverage is extremely low for Analytics | Low |
| 12.1 | Perf | In-memory caching leads to stale dashboards | High |
| 12.2 | Perf | Pagination missing on large datasets | High |
| 12.3 | Bug | Hardcoded timezone calculations | Medium |
| 12.4 | Security | Missing CSRF protection on API endpoints | Critical |



## 8. Data Import & Parsing Bugs

### 8.1 — HL7 parsing swallows `ValueError` for invalid ranges
**Affected files:** `tracker/views.py` (line ~785)
HL7 parsing uses a blanket `try: float(...) except ValueError: pass` which means invalid reference ranges silently result in no normal limits rather than failing or warning.

### 8.2 — FHIR JSON parsing is brittle and lacks schema validation
**Affected files:** `tracker/views.py` (JSON import section)
The JSON importer expects an exact FHIR "Bundle" and "Observation" shape and crashes with `KeyError` if an expected node is missing.

### 8.3 — CSV Importer `Exception` block hides data corruption
**Affected files:** `tracker/views.py` (CSV import section)
The import loops use bare `except Exception:` blocks, hiding database constraint errors or malformed row errors.

### 8.4 — OCR parsing fails on multi-page PDFs
**Affected files:** `tracker/views.py` (PDF OCR section)
The `pdfplumber` and `pytesseract` multi-pass logic does not properly loop over all pages or aggregate text cleanly, leading to lost data on page 2+.

---

## 9. Wearable & Telehealth Shortcomings

### 9.1 — Wearable APIs are entirely mocked
**Affected files:** `tracker/models.py`
Integrations like Fitbit, Garmin, and Oura have models but zero actual OAuth callback or HTTP request logic. `trigger_sync` creates empty data.

### 9.2 — `IntegrationSubTask` status changes don't trigger workflows
**Affected files:** `tracker/views.py`
Changing a subtask status to "completed" is a simple CRUD operation and doesn't fire signals to run actual data pipelines.

### 9.3 — OAuth credentials stored in plaintext
**Affected files:** `tracker/models.py` (WearableDevice)
The `access_token` and `refresh_token` are stored in plain `CharField` rather than being encrypted via the `EncryptionKey` mechanism.

### 9.4 — Telehealth links expire but no background cleanup
**Affected files:** `tracker/models.py`
`SecureViewingLink` entries pile up indefinitely. There is no Celery beat or management command to prune expired links.

---

## 10. Notifications & Alerts

### 10.1 — Critical Alerts trigger infinitely
**Affected files:** `tracker/views.py`
There is no "acknowledged" state or deduplication for `CriticalAlert`. The system checks thresholds and creates duplicates on every run.

### 10.2 — Notification templates lack escaping
**Affected files:** `tracker/views.py`
Using python's `.format()` or simple substitution for notifications allows potential injection if user-provided strings (e.g. test names) are included.

### 10.3 — Email delivery is synchronous
**Affected files:** `tracker/views.py` (StakeholderEmail)
Triggering stakeholder emails blocks the web request until the SMTP server responds, which can timeout the Gunicorn worker.

### 10.4 — Push notifications lack a provider
**Affected files:** `tracker/models.py` (NotificationLog)
The 'push' channel is defined but no APNS or FCM provider is integrated. The logs stay "pending" forever.

---

## 11. Testing & CI Pipeline

### 11.1 — Broken test suite due to syntax error
**Affected files:** `tracker/tests.py` (line 5243)
A misplaced `)` causes `SyntaxError` which completely breaks `manage.py test`.

### 11.2 — Test database migrations fail on conflicting leaf nodes
**Affected files:** `tracker/migrations/`
Multiple developers committed migrations simultaneously (`0014_add_language`, `0014_notification_system`, etc) causing `makemigrations --merge` to be required before tests can even create the schema.

### 11.3 — Test database migrations fail on `patient_id` duplicate column
**Affected files:** `tracker/migrations/`
Even after merging, running migrations produces `sqlite3.OperationalError: duplicate column name: patient_id` due to a bad schema operation.

### 11.4 — Coverage is extremely low for Analytics
**Affected files:** `tracker/tests.py`
Machine Learning and Predictive Analytics modules have 0% test coverage, rendering the stubs unverified.

---

## 12. Miscellaneous Backend Flaws

### 12.1 — In-memory caching leads to stale dashboards
**Affected files:** `tracker/views.py`
Phase 11 and Dashboard views cache heavy queries locally instead of using Redis, meaning multi-worker setups serve inconsistent data.

### 12.2 — Pagination missing on large datasets
**Affected files:** `tracker/views.py` (AuditLog list)
Audit logs and Vital Signs can grow to millions of rows, but the views attempt to render all of them without Django `Paginator`.

### 12.3 — Hardcoded timezone calculations
**Affected files:** `tracker/models.py`
Several models use `datetime.now()` instead of `timezone.now()`, which breaks when running the server in UTC but users are in local time.

### 12.4 — Missing CSRF protection on API endpoints
**Affected files:** `tracker/views.py`
Many JSON-returning views lack `@csrf_protect` or are not routed through Django REST Framework, exposing them to Cross-Site Request Forgery.
