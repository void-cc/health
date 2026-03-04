# Health Tracker

A comprehensive personal health tracking web application built with Django. Track blood test results, vital signs, body composition, nutrition, sleep, and much more — all in one place.

## Features

### Blood Tests & Lab Values
- Log, edit, and delete blood test results with normal range comparisons
- Manage blood test reference information (units, normal ranges, categories)
- Import lab data via **CSV**, **JSON**, **PDF (OCR)**, and **HL7/FHIR** formats
- Export data for offline use

### Data Visualization
- Interactive line charts with moving average overlays and anomaly highlighting
- Comparative bar charts against normal ranges
- Box-and-whisker plots for statistical distribution
- Correlative scatter plots (e.g. weight vs. blood pressure)
- Customizable date range selectors
- PDF export of charts and dashboards

### Vital Signs & Body Metrics
- Blood pressure, heart rate, weight, SpO₂, respiratory rate, and basal body temperature (BBT)
- Body composition: body fat %, skeletal muscle mass, bone density, waist-to-hip ratio
- Hydration logging with daily goals
- Energy & fatigue scoring (1–10 scale)
- Custom vital sign definitions
- Orthostatic tracking (supine vs. standing)
- Reproductive health tracking
- Resting Metabolic Rate (RMR) estimation
- Anatomical pain mapping

### Symptom & Metabolic Tracking
- Symptom journaling
- Blood glucose & insulin monitoring
- Ketone level tracking

### Nutrition & Sleep
- Macronutrient and micronutrient logging
- Food diary entries
- Intermittent fasting timers and logs
- Caffeine & alcohol consumption tracking
- Sleep architecture logging and quality scoring
- Circadian rhythm mapping
- Dream journal

### Dashboard & UX
- Customizable widget-based dashboards
- Bulk data editing interface
- Data point annotations
- Global search API

### Authentication & Security
- Secure registration and login with bcrypt/Argon2 password hashing
- Multi-Factor Authentication (MFA) via TOTP
- OAuth2 Single Sign-On (Google, Apple, Microsoft) *(placeholder)*
- Session management with inactivity timeouts
- Security activity logging
- Privacy preference centre
- Account deletion

### Wearable Integrations *(in progress)*
- Fitbit, Garmin, Oura Ring, Withings, Google Fit, Samsung Health, Strava, Dexcom *(stub)*

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | [Django 6](https://www.djangoproject.com/) |
| Database | PostgreSQL (via `psycopg2`) |
| Authentication | `django-allauth`, `django-otp` |
| OCR | `pytesseract`, `pdf2image`, `pdfplumber` |
| Fuzzy Matching | `thefuzz`, `python-Levenshtein` |
| Web Server | Gunicorn |

## Prerequisites

- Python 3.10+
- PostgreSQL
- Tesseract OCR (`tesseract-ocr` system package) — required for PDF import

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/void-cc/health.git
   cd health
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the database**

   Set the `DATABASE_URL` environment variable (PostgreSQL connection string):

   ```bash
   export DATABASE_URL="postgres://user:password@localhost:5432/health_db"
   ```

5. **Apply migrations**

   ```bash
   python manage.py migrate
   ```

6. **Seed reference data** *(optional)*

   ```bash
   python seed.py
   ```

## Running the Application

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

## Running Tests

```bash
python manage.py test
```

## Deployment

The project includes a `Procfile` for Heroku-compatible platforms:

```
web: gunicorn health_tracker.wsgi:application
```

Set `SECRET_KEY`, `DATABASE_URL`, and `DEBUG=False` in your environment before deploying.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development roadmap and feature checklist.

## License

This project is open source. See the repository for details.
