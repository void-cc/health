# Known Issues & Placeholder Features

This document is a complete audit of features that are either placeholder
implementations, unreachable through the UI, incorrectly implemented, or that
have a significant design gap between what they claim to do and what they
actually do.

---

## 1. Authentication & Access Control

### 1.1 — ~75 view functions are not protected by `@login_required`

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
- Integration views (`integration_config_activate`, `integration_config_run`,
  `phase11_dashboard`, `practitioner_access_edit`)

### 1.2 — RBAC roles are stored but never enforced

**Affected files:** `tracker/models.py` (`UserProfile`), `tracker/views.py`

`UserProfile.role` has three values (`admin`, `user`, `practitioner`) but
nowhere in the application is this field read to restrict or grant access to
any view or action. Any logged-in user can reach any page regardless of role.

### 1.3 — Admin user-management pages are accessible by all users

**Affected files:** `tracker/views.py`, `tracker/urls.py`

Pages under the **Administration** sidebar section (User Profiles, Family
Accounts, Consent Logs, Tenant Config, etc.) have no admin-only guard. Any
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

### 3.1 — `ClinicalTrialMatch` model has no views, URLs, or UI at all

**Affected files:** `tracker/models.py`, `tracker/views.py`, `tracker/urls.py`

The `ClinicalTrialMatch` model is imported in `views.py` but has no CRUD
views, no URL routes, and no sidebar entry. It is completely unreachable
through the application.

### 3.2 — `PharmacologicalInteraction` model has no views, URLs, or UI at all

**Affected files:** `tracker/models.py`, `tracker/views.py`, `tracker/urls.py`

Same situation as `ClinicalTrialMatch`. The model is defined and imported but
there is no way to view, create, edit, or delete interactions through the UI.
No drug-interaction checking is wired up to the Medications feature either.

### 3.3 — `wearable_device_sync` (line 1606) is never registered in `urls.py`

**Affected files:** `tracker/views.py` (line 1606), `tracker/urls.py`

A function `wearable_device_sync` exists at line 1606 that uses
`device.trigger_sync()`. It is not listed in `urlpatterns` and is therefore
completely unreachable.

### 3.4 — Duplicate `wearable_sync` definition — first is silently overridden

**Affected files:** `tracker/views.py` (lines 1722 and 3047)

There are two top-level functions named `wearable_sync`. Python (and Django)
will only use the second definition (line 3047). The first definition at
line 1722 (which carries `@login_required` and uses the OAuth integration
client) is silently discarded. The registered URL therefore points to the
second, undecorated version.

---

## 4. Placeholder / Stub Implementations

### 4.1 — `WearableDevice.trigger_sync()` creates empty placeholder records

**Affected files:** `tracker/models.py` (line 446)

The `trigger_sync` method always creates a `VitalSign` row with
`heart_rate=None, spo2=None` and nothing else, and (for most platforms) a
`SleepLog` row with only an auto-note. No real data from any wearable API is
fetched or imported; this is a stub that gives false positive "Sync completed"
messages.

### 4.2 — `IntegrationConfig.run_integration()` does nothing

**Affected files:** `tracker/models.py` (line 1629)

The method simply sets `last_run = timezone.now()` and saves, then returns
`(True, "Integration ran successfully")`. It performs no actual integration
work regardless of the `category` or `feature_type` selected.

### 4.3 — `DataExportRequest` supports CSV and PDF formats that are never generated

**Affected files:** `tracker/models.py` (`FORMAT_CHOICES`), `tracker/views.py`
(`data_export_download`)

`FORMAT_CHOICES` lists four formats: JSON, XML, CSV, PDF. The
`data_export_download` view only handles `xml` and falls back to JSON for
everything else. Selecting CSV or PDF produces a JSON file with a `.json`
extension.

### 4.4 — `APIRateLimitConfig` settings are stored but rate limiting is never enforced

**Affected files:** `tracker/models.py`, `tracker/views.py`, `tracker/middleware.py`

Users can create and configure per-endpoint rate limit rules, but there is no
middleware, decorator, or interceptor that reads these records and enforces
limits. The settings have no effect on request processing.

### 4.5 — `EncryptionKey` stores public keys but data is never encrypted

**Affected files:** `tracker/models.py`, `tracker/views.py`

The Encryption Keys admin page lets users register public keys, but no health
data is encrypted or decrypted anywhere in the application using these keys.

### 4.6 — `BackupConfiguration` has no scheduler or execution logic

**Affected files:** `tracker/models.py`, `tracker/views.py`

Backup configurations (name, frequency, retention days, storage location) can
be created and edited, but there is no Celery task, cron job, management
command, or any other mechanism that actually performs backups according to
these settings.

### 4.7 — `DatabaseScalingConfig` has no effect on the database

**Affected files:** `tracker/models.py`, `tracker/views.py`

Read replica, sharding, and partitioning configurations can be recorded, but
none of these settings are consumed by the Django database router or any
infrastructure code. They are data-entry-only placeholders.

### 4.8 — `AdminTelemetry` requires manual data entry

**Affected files:** `tracker/models.py`, `tracker/views.py`

Telemetry metrics (metric name + value) must be entered by hand via a form.
There is no agent, collector, or signal handler that auto-populates telemetry.
The feature is conceptually self-defeating.

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
| 1.1 | Auth | ~75 views missing `@login_required` | Critical |
| 1.2 | Auth | RBAC roles stored but never enforced | High |
| 1.3 | Auth | Admin pages accessible by all users | High |
| 2.1 | Data | No per-user data isolation on any model | High |
| 2.2 | Data | Secure links expose all users' data | High |
| 2.3 | Data | Practitioner portal exposes all users' data | High |
| 3.1 | Missing | `ClinicalTrialMatch` has no UI | Medium |
| 3.2 | Missing | `PharmacologicalInteraction` has no UI | Medium |
| 3.3 | Missing | `wearable_device_sync` not in `urls.py` | Medium |
| 3.4 | Bug | Duplicate `wearable_sync` — first silently overridden | Medium |
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
