# Health Tracker

A comprehensive personal health tracking web application built with Django. Track blood test results, vital signs, body composition, nutrition, sleep, and much more -- all in one unified platform. Designed for both individual users seeking to monitor their well-being and patients managing chronic conditions.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
  - [Blood Tests & Lab Values](#blood-tests--lab-values)
  - [Data Visualization](#data-visualization)
  - [Vital Signs & Body Metrics](#vital-signs--body-metrics)
  - [Symptom & Metabolic Tracking](#symptom--metabolic-tracking)
  - [Nutrition & Sleep](#nutrition--sleep)
  - [Dashboard & UX](#dashboard--ux)
  - [Authentication & Security](#authentication--security)
  - [Wearable Integrations](#wearable-integrations)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

Health Tracker is an open-source, robust health data management system. By allowing users to log varied metrics -- from routine lab results to daily vital signs -- and providing powerful visualization tools, this application enables users to identify trends, monitor abnormalities, and make data-driven decisions regarding their health. The application supports various data importation formats including CSV, JSON, HL7/FHIR, and OCR from PDF lab reports.

---

## Key Features

### Blood Tests & Lab Values
- Log, edit, and delete blood test results with automatic normal range comparisons.
- Manage blood test reference information including units, normal ranges, and categories.
- Import historical lab data via multiple formats: **CSV**, **JSON**, **PDF (OCR)**, and **HL7/FHIR**.
- Export data for offline use or to share with medical professionals.

### Data Visualization
- Interactive line charts featuring moving average overlays and anomaly highlighting.
- Comparative bar charts to visualize results against standard reference ranges.
- Box-and-whisker plots to show statistical distribution.
- Correlative scatter plots (e.g., analyzing weight versus blood pressure).
- Customizable date range selectors for precise trend analysis.
- PDF export capabilities for charts and comprehensive dashboards.

### Vital Signs & Body Metrics
- Comprehensive logging for blood pressure, heart rate, weight, SpO2, respiratory rate, and basal body temperature (BBT).
- Body composition tracking: body fat percentage, skeletal muscle mass, bone density, and waist-to-hip ratio.
- Hydration logging with personalized daily goals.
- Energy and fatigue scoring on a 1-10 qualitative scale.
- Custom vital sign definitions for specialized tracking needs.
- Orthostatic tracking to compare supine versus standing measurements.
- Reproductive health tracking modules.
- Resting Metabolic Rate (RMR) estimation algorithms.
- Interactive anatomical pain mapping.

### Symptom & Metabolic Tracking
- Structured symptom journaling to correlate feelings with quantitative data.
- Blood glucose and insulin level monitoring.
- Ketone level tracking for specific dietary or metabolic protocols.

### Nutrition & Sleep
- Macronutrient and micronutrient daily logging.
- Detailed food diary entries.
- Intermittent fasting timers and extensive logs.
- Caffeine and alcohol consumption tracking.
- Advanced sleep architecture logging and algorithmic quality scoring.
- Circadian rhythm mapping and dream journaling.

### Dashboard & UX
- Modular, customizable widget-based dashboard layouts.
- Bulk data editing interface resembling a spreadsheet for rapid corrections.
- Qualitative data point annotations directly on quantitative charts.
- Unified global search API for instantly finding tests, values, or journals.

### Authentication & Security
- Secure registration and login processes using bcrypt/Argon2 password hashing.
- Multi-Factor Authentication (MFA) utilizing Time-based One-Time Passwords (TOTP).
- Placeholders for OAuth2 Single Sign-On (Google, Apple, Microsoft).
- Advanced session management including strict inactivity timeouts.
- User-facing security activity logging for auditing logins and devices.
- Centralized privacy preference center and self-service account deletion.

### Wearable Integrations
- Work in progress integrations for syncing with Fitbit, Garmin, Oura Ring, Withings, Google Fit, Samsung Health, Strava, and Dexcom.

---

## Tech Stack

The application leverages a modern, robust technology stack tailored for security, scalability, and data processing capabilities.

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | [Django 6](https://www.djangoproject.com/) |
| **Database** | PostgreSQL (accessed via `psycopg2`) |
| **Authentication** | `django-allauth`, `django-otp` |
| **OCR & Processing** | `pytesseract`, `pdf2image`, `pdfplumber` |
| **Fuzzy Matching** | `thefuzz`, `python-Levenshtein` |
| **Web Server** | Gunicorn |

---

## Getting Started

Follow these instructions to set up a local development environment.

### Prerequisites

Ensure you have the following installed on your local machine:
- **Python 3.10+**
- **PostgreSQL** (or compatible database)
- **Tesseract OCR** (System package `tesseract-ocr` is strictly required for the PDF import functionality)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/void-cc/health.git
   cd health
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**
   Ensure your virtual environment is active, then install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. **Configure the database**
   Set the `DATABASE_URL` environment variable to match your local PostgreSQL connection string:
   ```bash
   export DATABASE_URL="postgres://user:password@localhost:5432/health_db"
   ```
   If unset, the application may default to an SQLite database (not recommended for production).

2. **Apply migrations**
   Initialize the database schema:
   ```bash
   python manage.py migrate
   ```

3. **Seed reference data (Optional)**
   Populate the database with initial reference test values:
   ```bash
   python seed.py
   ```

### Running the Application

Start the Django development server:
```bash
python manage.py runserver
```

The application will now be available locally at `http://127.0.0.1:8000/`.

---

## Testing

The project includes a comprehensive test suite covering data importation, visualization generation, and core modeling.

To run the full test suite:
```bash
python manage.py test
```

If you prefer using `pytest` directly, ensure the Django environment is configured beforehand:
```bash
export DJANGO_SETTINGS_MODULE=health_tracker.settings
pytest
```

---

## Deployment

The project is designed to be easily deployable on Heroku-compatible PaaS providers. It includes a `Procfile` defining the web process:

```text
web: gunicorn health_tracker.wsgi:application
```

OS-level dependencies (such as `tesseract-ocr` and `poppler-utils`) are defined in the included `Aptfile`.

Before deploying to a production environment, ensure the following environment variables are properly configured:
- `SECRET_KEY`: A long, cryptographically secure random string.
- `DATABASE_URL`: Your production database connection string.
- `DEBUG`: Must be set to `False`.

---

## Contributing

We welcome contributions! To contribute to Health Tracker:
1. Fork the repository.
2. Create a new branch for your feature or bugfix (`git checkout -b feature/your-feature-name`).
3. Commit your changes with descriptive messages.
4. Push to your branch (`git push origin feature/your-feature-name`).
5. Open a Pull Request detailing your changes.

Please refer to the `AGENTS.md` and `ISSUES.md` (if present) for more specific guidelines on development personas and tracking current tasks.

---

## Roadmap

The project has an extensive, multi-phase roadmap encompassing advanced analytics, predictive modeling, machine learning integration, and deep interoperability (IHE_XDM, FHIR R4).

See [ROADMAP.md](ROADMAP.md) for the full developmental checklist spanning over 900+ sub-tasks.

---

## License

This project is open-source. Please see the repository files for specific licensing details.
