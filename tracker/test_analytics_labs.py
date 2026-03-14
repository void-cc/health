from django.test import TestCase
from django.contrib.auth.models import User
from tracker.models import BloodTest, VitalSign, Measurement, MeasurementType
from tracker.services.analytics.labs import build_timeline_events
from datetime import date, datetime, timedelta
from django.utils import timezone

class TimelineEventsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_empty_data(self):
        """Ensures the function returns an empty list when no data is present."""
        events = build_timeline_events(self.user)
        self.assertEqual(events, [])

    def test_sorting_order(self):
        """Verifies that events are sorted newest-first across all models."""
        # Vital sign - oldest
        VitalSign.objects.create(user=self.user, date=date(2023, 1, 1), heart_rate=70)
        # Blood test - middle
        BloodTest.objects.create(user=self.user, test_name="Glucose", value=90, unit="mg/dL", date=date(2023, 1, 2))
        # Measurement - newest
        mtype = MeasurementType.objects.create(name="Weight")
        Measurement.objects.create(
            user=self.user,
            measurement_type=mtype,
            value=70,
            unit="kg",
            observed_at=timezone.make_aware(datetime(2023, 1, 3)),
            is_confirmed=True
        )

        events = build_timeline_events(self.user)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]['type'], 'measurement')
        self.assertEqual(events[1]['type'], 'blood_test')
        self.assertEqual(events[2]['type'], 'vital_sign')

    def test_limit_parameter(self):
        """Checks that the function respects the limit argument."""
        for i in range(10):
            VitalSign.objects.create(user=self.user, date=date(2023, 1, 1) + timedelta(days=i), heart_rate=70+i)

        events = build_timeline_events(self.user, limit=5)
        self.assertEqual(len(events), 5)

    def test_blood_test_deltas(self):
        """Verifies that deltas (percentage change) are correctly calculated for blood tests."""
        # Previous
        BloodTest.objects.create(user=self.user, test_name="Glucose", value=100, unit="mg/dL", date=date(2023, 1, 1))
        # Latest
        BloodTest.objects.create(user=self.user, test_name="Glucose", value=110, unit="mg/dL", date=date(2023, 1, 2))

        events = build_timeline_events(self.user)
        glucose_event = next(e for e in events if e['title'] == 'Glucose' and e['date'] == date(2023, 1, 2))
        # Details are formatted as "value unit · arrow pct% since last"
        self.assertIn("↑ 10.0% since last", glucose_event['details'])

    def test_blood_test_badges(self):
        """Ensures correct 'high'/'low' badges are assigned based on normal ranges."""
        # High
        BloodTest.objects.create(
            user=self.user, test_name="Glucose", value=120, unit="mg/dL", date=date(2023, 1, 1),
            normal_min=70, normal_max=100
        )
        # Low
        BloodTest.objects.create(
            user=self.user, test_name="Iron", value=40, unit="ug/dL", date=date(2023, 1, 2),
            normal_min=60, normal_max=170
        )

        events = build_timeline_events(self.user)
        glucose_event = next(e for e in events if e['title'] == 'Glucose')
        iron_event = next(e for e in events if e['title'] == 'Iron')

        self.assertEqual(glucose_event['badge'], 'high')
        self.assertEqual(iron_event['badge'], 'low')

    def test_confirmed_measurements_only(self):
        """Confirms that only is_confirmed=True Measurements are included."""
        mtype = MeasurementType.objects.create(name="Weight")
        # Confirmed
        Measurement.objects.create(
            user=self.user, measurement_type=mtype, value=70, unit="kg",
            observed_at=timezone.now(), is_confirmed=True
        )
        # Unconfirmed
        Measurement.objects.create(
            user=self.user, measurement_type=mtype, value=71, unit="kg",
            observed_at=timezone.now(), is_confirmed=False
        )

        events = build_timeline_events(self.user)
        measurement_events = [e for e in events if e['type'] == 'measurement']
        self.assertEqual(len(measurement_events), 1)
        self.assertEqual(measurement_events[0]['details'], "70.0 kg")

    def test_vital_signs_details(self):
        """Checks that vital sign details string is correctly formatted."""
        VitalSign.objects.create(
            user=self.user, date=date(2023, 1, 1),
            heart_rate=72, systolic_bp=120, diastolic_bp=80, weight=70.5, spo2=98.0
        )

        events = build_timeline_events(self.user)
        vs_event = events[0]
        # VitalSigns code uses: HR 72 bpm · BP 120/80 · Weight 70.5 kg · SpO₂ 98.0%
        self.assertEqual(vs_event['details'], "HR 72 bpm · BP 120/80 · Weight 70.5 kg · SpO₂ 98.0%")
