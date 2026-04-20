## 2024-05-18 - [Hardcoded Django Settings]
**Vulnerability:** Hardcoded `SECRET_KEY` and `DEBUG = True` in `health_tracker/settings.py`.
**Learning:** Default Django generated settings can leak into production if not parameterized with environment variables, exposing the application to secret key forgery and sensitive information disclosure via debug pages.
**Prevention:** Always initialize new Django projects with `os.environ.get()` for sensitive keys and boolean flags.
