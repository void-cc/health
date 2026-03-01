import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_tracker.settings")
django.setup()

from tracker.models import BloodTest
from datetime import date

# Insert a dummy test record
BloodTest.objects.create(
    test_name="Hemoglobin",
    value=15.0,
    unit="g/dL",
    date=date.today(),
    normal_min=13.8,
    normal_max=17.2,
)

# Below normal range
BloodTest.objects.create(
    test_name="Hemoglobin",
    value=12.0,
    unit="g/dL",
    date=date.today(),
    normal_min=13.8,
    normal_max=17.2,
)

# Above normal range
BloodTest.objects.create(
    test_name="Hemoglobin",
    value=18.0,
    unit="g/dL",
    date=date.today(),
    normal_min=13.8,
    normal_max=17.2,
)

print("Database seeded with test values.")
