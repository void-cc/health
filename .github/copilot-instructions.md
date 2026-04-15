# Copilot Instructions for Health Tracker

This is a Django-based personal health tracking web application. It allows users to log and visualize blood test results, vital signs, body composition, nutrition, sleep, medications, and more.

## Tech Stack

- **Backend**: Django 6 (Python 3.10+)
- **Database**: PostgreSQL (via `psycopg2`; SQLite used in tests)
- **Authentication**: `django-allauth`, `django-otp`
- **OCR**: `pytesseract`, `pdf2image`, `pdfplumber`
- **Fuzzy Matching**: `thefuzz`, `python-Levenshtein`
- **Web Server**: Gunicorn

## Repository Structure

- `health_tracker/` – Django project settings, URLs, WSGI/ASGI config
- `tracker/` – Main Django app: models, views, forms, URLs, tests, integrations
- `tracker/integrations/` – Wearable device integration clients (Fitbit, Garmin, etc.)
- `tracker/migrations/` – Django database migrations
- `tracker/templatetags/` – Custom Django template filters and tags
- `templates/` – HTML templates
- `static/` – Static assets (CSS, JS, images)
- `requirements.txt` – Python dependencies
- `manage.py` – Django management script
- `seed.py` – Script to seed reference data (blood test info)
- `test_parsing.py` – CSV/JSON import parsing tests
- `test_hl7_fhir.py` – HL7/FHIR parsing tests

## Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the database** (PostgreSQL connection string):
   ```bash
   export DATABASE_URL="postgres://user:password@localhost:5432/health_db"
   ```
   Tests use SQLite and do not require a running PostgreSQL instance.

3. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

4. **Seed reference data** *(optional)*
   ```bash
   python seed.py
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Running Tests

Run the full Django test suite:
```bash
python manage.py test
```

Run a specific test class or module:
```bash
python manage.py test tracker.tests.VitalSignTests --verbosity 2
```

Run the standalone parsing tests:
```bash
python test_parsing.py
python test_hl7_fhir.py
```

The CI test matrix (`.github/workflows/tests.yml`) groups tests by feature phase. New tests should be added to `tracker/tests.py` in the appropriate phase class, or in a new class following the same naming convention (e.g. `PhaseNFeatureTests`).

## Code Standards

- Follow standard Django project conventions: fat models, thin views, forms for validation.
- Keep business logic in models or service-level helpers, not in views.
- Use Django's built-in `TestCase` for all tests; avoid third-party test frameworks.
- New models must include a `__str__` method and be registered in `tracker/admin.py`.
- New URL patterns belong in `tracker/urls.py`; use named URLs with `reverse()` in tests.
- Use Django's ORM exclusively — no raw SQL unless absolutely necessary.
- Sensitive user data must never be logged or exposed in error messages.

## Key Guidelines

1. Write tests for all new models, views, and forms. Use the existing test classes in `tracker/tests.py` as a reference.
2. Run `python manage.py migrate` after adding or modifying models.
3. Keep migrations small and focused; avoid editing existing migrations.
4. When adding new pip dependencies, add them to `requirements.txt`.
5. Templates live in `templates/`; extend `base.html` for consistent layout.
6. Authentication and access control: all health-data views must require login (`@login_required` or `LoginRequiredMixin`).

## Design Context

### Users
Primary users are patients who use the app to monitor personal health trends over time and make informed day-to-day decisions. Secondary users are caregivers and practitioners who need quick, trustworthy interpretation of patient data in shared review contexts. The core job to be done is to turn complex health inputs into clear, low-friction understanding through dashboards, trend views, and comparison tools.

### Brand Personality
The product voice is clinical, data-driven, and clean. It should feel calm and informative rather than alarmist, with emphasis on clarity, reliability, and evidence-oriented presentation. The interface should support trust in medical-style workflows while remaining approachable for regular daily use.

### Aesthetic Direction
Preferred visual direction is elegant and technical. The UI should prioritize light mode with clean surfaces, strong typographic hierarchy, restrained color usage, and information-dense but breathable layouts. Existing design signals in the codebase (structured cards, semantic status colors, accessibility-minded patterns, and chart-centric views) should be reinforced and made more cohesive over time.

### Design Principles
1. Calm clarity over visual noise: reduce cognitive load and help users understand status quickly.
2. Data legibility first: optimize hierarchy, spacing, and contrast for scanability in dashboards and tables.
3. Clinical trustworthiness: use precise language, consistent patterns, and predictable interactions.
4. Elegant technical execution: keep visuals modern and polished without becoming decorative.
5. Inclusive by default: maintain accessibility-conscious patterns as a baseline, improving iteratively on a best-effort basis.
