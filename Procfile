release: python manage.py migrate && python manage.py compilemessages
web: gunicorn health_tracker.wsgi:application
