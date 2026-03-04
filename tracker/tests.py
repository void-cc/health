from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from tracker.models import (
    BloodTest, BloodTestInfo, VitalSign, DataPointAnnotation, DashboardWidget,
    UserProfile, SecurityLog, UserSession, PrivacyPreference,
    SecureViewingLink, PractitionerAccess, IntakeSummary,
    DataExportRequest, StakeholderEmail, MedicationSchedule,
    SleepLog, MacronutrientLog, FastingLog, MetabolicLog,
    HealthGoal, CriticalAlert, WearableDevice, WearableSyncLog,
    HealthReport, PredictiveBiomarker, BiologicalAgeCalculation,
    IntegrationConfig, BodyComposition,
)
from datetime import date, datetime, timedelta
from django.utils import timezone
import json


class TemplateFilterTests(TestCase):
    def test_tojson_filter(self):
        from tracker.templatetags.json_filters import tojson
        self.assertEqual(tojson([1, 2, 3]), '[1, 2, 3]')
        self.assertEqual(tojson({"key": "value"}), '{"key": "value"}')
        # Test XSS escaping
        result = tojson("<script>alert('xss')</script>")
        self.assertNotIn('<script>', str(result))
        self.assertIn('\\u003C', str(result))

    def test_lookup_filter(self):
        from tracker.templatetags.json_filters import lookup
        d = {1: "one", 2: "two"}
        self.assertEqual(lookup(d, 1), "one")
        self.assertIsNone(lookup(d, 3))
        self.assertIsNone(lookup("not a dict", 1))


class ViewStatusCodeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_history_page(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)

    def test_vitals_page(self):
        response = self.client.get(reverse('vitals'))
        self.assertEqual(response.status_code, 200)

    def test_add_test_page(self):
        response = self.client.get(reverse('add_test'))
        self.assertEqual(response.status_code, 200)

    def test_add_test_info_page(self):
        response = self.client.get(reverse('add_test_info'))
        self.assertEqual(response.status_code, 200)

    def test_add_vitals_page(self):
        response = self.client.get(reverse('add_vitals'))
        self.assertEqual(response.status_code, 200)

    def test_blood_tests_charts_page(self):
        response = self.client.get(reverse('blood_tests_charts'))
        self.assertEqual(response.status_code, 200)

    def test_blood_tests_boxplots_page(self):
        response = self.client.get(reverse('blood_tests_boxplots'))
        self.assertEqual(response.status_code, 200)

    def test_comparative_bar_charts_page(self):
        response = self.client.get(reverse('comparative_bar_charts'))
        self.assertEqual(response.status_code, 200)

    def test_vitals_charts_page(self):
        response = self.client.get(reverse('vitals_charts'))
        self.assertEqual(response.status_code, 200)

    def test_scatter_plots_page(self):
        response = self.client.get(reverse('scatter_plots'))
        self.assertEqual(response.status_code, 200)

    def test_import_data_page(self):
        response = self.client.get(reverse('import_data'))
        self.assertEqual(response.status_code, 200)

    def test_export_data(self):
        response = self.client.get(reverse('export_data'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')


class ViewWithDataTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        self.test_info = BloodTestInfo.objects.create(
            test_name="Hemoglobin", unit="g/dL",
            normal_min=13.8, normal_max=17.2, category="Blood Count"
        )
        self.blood_test = BloodTest.objects.create(
            test_name="Hemoglobin", value=15.0, unit="g/dL",
            date=date(2026, 1, 15), normal_min=13.8, normal_max=17.2,
            category="Blood Count"
        )
        self.vital = VitalSign.objects.create(
            date=date(2026, 1, 15), weight=70.5, heart_rate=72,
            systolic_bp=120, diastolic_bp=80
        )

    def test_index_with_data(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hemoglobin')
        self.assertContains(response, '15.0')

    def test_history_with_data(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2026-01-15')

    def test_history_filter_form_present(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'filter-search')
        self.assertContains(response, 'filter-type')
        self.assertContains(response, 'filter-status')
        self.assertContains(response, 'filter-date-from')
        self.assertContains(response, 'filter-date-to')

    def test_history_filter_by_type_blood_test(self):
        response = self.client.get(reverse('history'), {'type': 'Blood Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hemoglobin')
        self.assertNotContains(response, 'Vital Signs')

    def test_history_filter_by_type_vitals(self):
        response = self.client.get(reverse('history'), {'type': 'Vitals'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Hemoglobin')
        self.assertContains(response, 'Vital Signs')

    def test_history_filter_by_status_normal(self):
        response = self.client.get(reverse('history'), {'status': 'Normal'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'badge-success')
        self.assertNotContains(response, 'badge-danger')

    def test_history_filter_by_status_out_of_range(self):
        # Create a blood test that is out of range
        BloodTest.objects.create(
            test_name='Glucose', value=200.0, unit='mg/dL',
            date=date(2026, 1, 20), normal_min=70.0, normal_max=100.0,
        )
        response = self.client.get(reverse('history'), {'status': 'Out of Range'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Glucose')
        self.assertNotContains(response, 'Hemoglobin')

    def test_history_filter_by_date_from(self):
        BloodTest.objects.create(
            test_name='Cholesterol', value=180.0, unit='mg/dL',
            date=date(2025, 6, 1), normal_min=0.0, normal_max=200.0,
        )
        response = self.client.get(reverse('history'), {'date_from': '2026-01-01'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hemoglobin')
        self.assertNotContains(response, 'Cholesterol')

    def test_history_filter_by_date_to(self):
        BloodTest.objects.create(
            test_name='Cholesterol', value=180.0, unit='mg/dL',
            date=date(2025, 6, 1), normal_min=0.0, normal_max=200.0,
        )
        response = self.client.get(reverse('history'), {'date_to': '2025-12-31'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cholesterol')
        self.assertNotContains(response, 'Hemoglobin')

    def test_history_filter_by_search(self):
        response = self.client.get(reverse('history'), {'search': 'Hemo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hemoglobin')

    def test_history_filter_search_no_match(self):
        response = self.client.get(reverse('history'), {'search': 'Xyznonexistent'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No results match your filters')

    def test_history_active_filter_badges(self):
        response = self.client.get(reverse('history'), {'type': 'Blood Test', 'status': 'Normal'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active filters:')
        self.assertContains(response, 'Type: Blood Test')
        self.assertContains(response, 'Status: Normal')

    def test_vitals_with_data(self):
        response = self.client.get(reverse('vitals'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '70.5')

    def test_chart_page(self):
        response = self.client.get(reverse('chart', kwargs={'test_name': 'Hemoglobin'}))
        self.assertEqual(response.status_code, 200)

    def test_edit_test_page(self):
        response = self.client.get(reverse('edit_test', kwargs={'test_id': self.blood_test.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2026-01-15')

    def test_edit_vitals_page(self):
        response = self.client.get(reverse('edit_vitals', kwargs={'vital_id': self.vital.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '70.5')

    def test_blood_tests_charts_with_data(self):
        response = self.client.get(reverse('blood_tests_charts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hemoglobin')

    def test_blood_tests_charts_has_date_filter(self):
        response = self.client.get(reverse('blood_tests_charts'))
        self.assertContains(response, 'startDate')
        self.assertContains(response, 'endDate')
        self.assertContains(response, 'Apply Filter')

    def test_blood_tests_charts_has_moving_avg_toggle(self):
        response = self.client.get(reverse('blood_tests_charts'))
        self.assertContains(response, 'toggleMovingAvg')
        self.assertContains(response, 'Moving Average')

    def test_blood_tests_charts_has_anomaly_toggle(self):
        response = self.client.get(reverse('blood_tests_charts'))
        self.assertContains(response, 'toggleAnomaly')
        self.assertContains(response, 'Anomaly Detection')

    def test_vitals_charts_has_date_filter(self):
        response = self.client.get(reverse('vitals_charts'))
        self.assertContains(response, 'startDate')
        self.assertContains(response, 'endDate')
        self.assertContains(response, 'Apply Filter')

    def test_vitals_charts_has_moving_avg_toggle(self):
        response = self.client.get(reverse('vitals_charts'))
        self.assertContains(response, 'toggleMovingAvg')
        self.assertContains(response, 'Moving Average')

    def test_vitals_charts_has_anomaly_toggle(self):
        response = self.client.get(reverse('vitals_charts'))
        self.assertContains(response, 'toggleAnomaly')
        self.assertContains(response, 'Anomaly Detection')

    def test_scatter_plots_with_data(self):
        response = self.client.get(reverse('scatter_plots'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Correlative Scatter Plots')
        self.assertContains(response, 'Hemoglobin')
        self.assertContains(response, 'Weight')

    def test_comparative_bar_charts_with_data(self):
        response = self.client.get(reverse('comparative_bar_charts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hemoglobin')

    def test_export_with_data(self):
        response = self.client.get(reverse('export_data'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Hemoglobin', response.content.decode())

    def test_add_test_post(self):
        response = self.client.post(reverse('add_test'), {
            'date': '2026-02-01',
            'test_names': ['Hemoglobin'],
            'values[Hemoglobin]': '14.5',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloodTest.objects.count(), 2)

    def test_delete_test_post(self):
        response = self.client.post(reverse('delete_test', kwargs={'test_id': self.blood_test.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloodTest.objects.count(), 0)

    def test_add_vitals_post(self):
        response = self.client.post(reverse('add_vitals'), {
            'date': '2026-02-01',
            'weight': '75.0',
            'heart_rate': '68',
            'systolic_bp': '118',
            'diastolic_bp': '78',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VitalSign.objects.count(), 2)

    def test_delete_vitals_post(self):
        response = self.client.post(reverse('delete_vitals', kwargs={'vital_id': self.vital.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VitalSign.objects.count(), 0)


# ===== Model Tests =====

from tracker.models import (
    BodyComposition, HydrationLog, EnergyFatigueLog,
    CustomVitalDefinition, CustomVitalEntry, PainLog,
    RestingMetabolicRate, OrthostaticReading, ReproductiveHealthLog,
    SymptomJournal, MetabolicLog, KetoneLog,
)


class Phase2ModelTests(TestCase):
    """Test model creation, __str__, and calculated fields for these models."""

    def test_body_composition_waist_to_hip_ratio(self):
        bc = BodyComposition.objects.create(
            date=date(2026, 3, 1),
            body_fat_percentage=18.5,
            waist_circumference=80.0,
            hip_circumference=100.0,
        )
        self.assertEqual(bc.waist_to_hip_ratio, 0.8)

    def test_body_composition_str(self):
        bc = BodyComposition.objects.create(date=date(2026, 3, 1))
        self.assertEqual(str(bc), "Body Composition on 2026-03-01")

    def test_hydration_goal_percentage(self):
        h = HydrationLog.objects.create(
            date=date(2026, 3, 1), fluid_intake_ml=2000, goal_ml=2500,
        )
        self.assertEqual(h.goal_percentage, 80.0)

    def test_hydration_goal_percentage_none(self):
        h = HydrationLog.objects.create(
            date=date(2026, 3, 1), fluid_intake_ml=2000, goal_ml=0,
        )
        self.assertIsNone(h.goal_percentage)

    def test_hydration_str(self):
        h = HydrationLog.objects.create(
            date=date(2026, 3, 1), fluid_intake_ml=1500.0,
        )
        self.assertIn("Hydration on 2026-03-01", str(h))
        self.assertIn("1500", str(h))
        self.assertIn("ml", str(h))

    def test_energy_str(self):
        e = EnergyFatigueLog.objects.create(
            date=date(2026, 3, 1), energy_score=7,
        )
        self.assertEqual(str(e), "Energy on 2026-03-01: 7/10")

    def test_custom_vital_definition_str(self):
        d = CustomVitalDefinition.objects.create(name="Grip Strength", unit="kg")
        self.assertEqual(str(d), "Grip Strength (kg)")

    def test_custom_vital_entry_str(self):
        d = CustomVitalDefinition.objects.create(name="Grip Strength", unit="kg")
        entry = CustomVitalEntry.objects.create(
            definition=d, date=date(2026, 3, 1), value=45.0,
        )
        self.assertEqual(str(entry), "Grip Strength on 2026-03-01: 45.0")

    def test_pain_log_str(self):
        p = PainLog.objects.create(
            date=date(2026, 3, 1), body_region='lower_back', pain_level=6,
        )
        self.assertEqual(str(p), "Pain on 2026-03-01: Lower Back (6/10)")

    def test_rmr_mifflin_male(self):
        rmr = RestingMetabolicRate(
            date=date(2026, 3, 1), age=30, weight_kg=80,
            height_cm=180, gender='M', formula='mifflin',
        )
        expected = round(10 * 80 + 6.25 * 180 - 5 * 30 + 5, 1)
        self.assertEqual(rmr.calculate_rmr(), expected)

    def test_rmr_mifflin_female(self):
        rmr = RestingMetabolicRate(
            date=date(2026, 3, 1), age=25, weight_kg=60,
            height_cm=165, gender='F', formula='mifflin',
        )
        expected = round(10 * 60 + 6.25 * 165 - 5 * 25 - 161, 1)
        self.assertEqual(rmr.calculate_rmr(), expected)

    def test_rmr_harris_male(self):
        rmr = RestingMetabolicRate(
            date=date(2026, 3, 1), age=30, weight_kg=80,
            height_cm=180, gender='M', formula='harris',
        )
        expected = round(88.362 + 13.397 * 80 + 4.799 * 180 - 5.677 * 30, 1)
        self.assertEqual(rmr.calculate_rmr(), expected)

    def test_rmr_harris_female(self):
        rmr = RestingMetabolicRate(
            date=date(2026, 3, 1), age=25, weight_kg=60,
            height_cm=165, gender='F', formula='harris',
        )
        expected = round(447.593 + 9.247 * 60 + 3.098 * 165 - 4.330 * 25, 1)
        self.assertEqual(rmr.calculate_rmr(), expected)

    def test_rmr_auto_calculates_on_save(self):
        rmr = RestingMetabolicRate.objects.create(
            date=date(2026, 3, 1), age=30, weight_kg=80,
            height_cm=180, gender='M', formula='mifflin',
        )
        self.assertIsNotNone(rmr.rmr_value)
        expected = round(10 * 80 + 6.25 * 180 - 5 * 30 + 5, 1)
        self.assertEqual(rmr.rmr_value, expected)

    def test_rmr_str(self):
        rmr = RestingMetabolicRate.objects.create(
            date=date(2026, 3, 1), age=30, weight_kg=80,
            height_cm=180, gender='M', formula='mifflin',
        )
        self.assertIn("RMR on 2026-03-01", str(rmr))
        self.assertIn("kcal/day", str(rmr))

    def test_orthostatic_hr_difference(self):
        o = OrthostaticReading.objects.create(
            date=date(2026, 3, 1), supine_hr=60, standing_hr=85,
        )
        self.assertEqual(o.hr_difference, 25)

    def test_orthostatic_systolic_drop(self):
        o = OrthostaticReading.objects.create(
            date=date(2026, 3, 1), supine_systolic=120, standing_systolic=105,
        )
        self.assertEqual(o.systolic_drop, 15)

    def test_orthostatic_hr_difference_none(self):
        o = OrthostaticReading.objects.create(date=date(2026, 3, 1))
        self.assertIsNone(o.hr_difference)

    def test_orthostatic_systolic_drop_none(self):
        o = OrthostaticReading.objects.create(date=date(2026, 3, 1))
        self.assertIsNone(o.systolic_drop)

    def test_orthostatic_str(self):
        o = OrthostaticReading.objects.create(date=date(2026, 3, 1))
        self.assertEqual(str(o), "Orthostatic on 2026-03-01")

    def test_reproductive_str(self):
        r = ReproductiveHealthLog.objects.create(
            date=date(2026, 3, 1), cycle_day=14, phase='ovulation',
        )
        self.assertEqual(str(r), "Reproductive Health on 2026-03-01")

    def test_symptom_str(self):
        s = SymptomJournal.objects.create(
            date=date(2026, 3, 1), symptom='Headache', severity=3,
        )
        self.assertEqual(str(s), "Headache on 2026-03-01 (severity: 3)")

    def test_metabolic_str(self):
        m = MetabolicLog.objects.create(
            date=date(2026, 3, 1), blood_glucose=95.0,
        )
        self.assertEqual(str(m), "Metabolic on 2026-03-01")

    def test_ketone_str(self):
        k = KetoneLog.objects.create(
            date=date(2026, 3, 1), value=0.8, measurement_type='blood',
        )
        self.assertEqual(str(k), "Ketone on 2026-03-01: 0.8 (Blood (mmol/L))")


class Phase2StatusCodeTests(TestCase):
    """Test GET requests return 200 for all Vital Signs list and add pages."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_body_composition_list(self):
        response = self.client.get(reverse('body_composition_list'))
        self.assertEqual(response.status_code, 200)

    def test_body_composition_add(self):
        response = self.client.get(reverse('body_composition_add'))
        self.assertEqual(response.status_code, 200)

    def test_hydration_list(self):
        response = self.client.get(reverse('hydration_list'))
        self.assertEqual(response.status_code, 200)

    def test_hydration_add(self):
        response = self.client.get(reverse('hydration_add'))
        self.assertEqual(response.status_code, 200)

    def test_energy_list(self):
        response = self.client.get(reverse('energy_list'))
        self.assertEqual(response.status_code, 200)

    def test_energy_add(self):
        response = self.client.get(reverse('energy_add'))
        self.assertEqual(response.status_code, 200)

    def test_custom_vitals_list(self):
        response = self.client.get(reverse('custom_vitals_list'))
        self.assertEqual(response.status_code, 200)

    def test_custom_vital_define(self):
        response = self.client.get(reverse('custom_vital_define'))
        self.assertEqual(response.status_code, 200)

    def test_custom_vital_add_entry(self):
        response = self.client.get(reverse('custom_vital_add_entry'))
        self.assertEqual(response.status_code, 200)

    def test_pain_list(self):
        response = self.client.get(reverse('pain_list'))
        self.assertEqual(response.status_code, 200)

    def test_pain_add(self):
        response = self.client.get(reverse('pain_add'))
        self.assertEqual(response.status_code, 200)

    def test_rmr_list(self):
        response = self.client.get(reverse('rmr_list'))
        self.assertEqual(response.status_code, 200)

    def test_rmr_add(self):
        response = self.client.get(reverse('rmr_add'))
        self.assertEqual(response.status_code, 200)

    def test_orthostatic_list(self):
        response = self.client.get(reverse('orthostatic_list'))
        self.assertEqual(response.status_code, 200)

    def test_orthostatic_add(self):
        response = self.client.get(reverse('orthostatic_add'))
        self.assertEqual(response.status_code, 200)

    def test_reproductive_list(self):
        response = self.client.get(reverse('reproductive_list'))
        self.assertEqual(response.status_code, 200)

    def test_reproductive_add(self):
        response = self.client.get(reverse('reproductive_add'))
        self.assertEqual(response.status_code, 200)

    def test_symptom_list(self):
        response = self.client.get(reverse('symptom_list'))
        self.assertEqual(response.status_code, 200)

    def test_symptom_add(self):
        response = self.client.get(reverse('symptom_add'))
        self.assertEqual(response.status_code, 200)

    def test_metabolic_list(self):
        response = self.client.get(reverse('metabolic_list'))
        self.assertEqual(response.status_code, 200)

    def test_metabolic_add(self):
        response = self.client.get(reverse('metabolic_add'))
        self.assertEqual(response.status_code, 200)

    def test_ketone_list(self):
        response = self.client.get(reverse('ketone_list'))
        self.assertEqual(response.status_code, 200)

    def test_ketone_add(self):
        response = self.client.get(reverse('ketone_add'))
        self.assertEqual(response.status_code, 200)


class Phase2CRUDTests(TestCase):
    """Test POST create, edit, and delete for each Vital Signs module."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    # ----- Body Composition -----
    def test_body_composition_add_post(self):
        response = self.client.post(reverse('body_composition_add'), {
            'date': '2026-03-01',
            'body_fat_percentage': '18.5',
            'waist_circumference': '80',
            'hip_circumference': '100',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BodyComposition.objects.count(), 1)
        bc = BodyComposition.objects.first()
        self.assertEqual(bc.waist_to_hip_ratio, 0.8)

    def test_body_composition_edit_post(self):
        bc = BodyComposition.objects.create(
            date=date(2026, 3, 1), body_fat_percentage=18.5,
        )
        response = self.client.post(reverse('body_composition_edit', kwargs={'pk': bc.pk}), {
            'date': '2026-03-02',
            'body_fat_percentage': '20.0',
        })
        self.assertEqual(response.status_code, 302)
        bc.refresh_from_db()
        self.assertEqual(bc.body_fat_percentage, 20.0)

    def test_body_composition_delete_post(self):
        bc = BodyComposition.objects.create(date=date(2026, 3, 1))
        response = self.client.post(reverse('body_composition_delete', kwargs={'pk': bc.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BodyComposition.objects.count(), 0)

    # ----- Hydration -----
    def test_hydration_add_post(self):
        response = self.client.post(reverse('hydration_add'), {
            'date': '2026-03-01',
            'fluid_intake_ml': '2000',
            'goal_ml': '2500',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HydrationLog.objects.count(), 1)

    def test_hydration_edit_post(self):
        h = HydrationLog.objects.create(
            date=date(2026, 3, 1), fluid_intake_ml=2000,
        )
        response = self.client.post(reverse('hydration_edit', kwargs={'pk': h.pk}), {
            'date': '2026-03-01',
            'fluid_intake_ml': '2500',
            'goal_ml': '3000',
        })
        self.assertEqual(response.status_code, 302)
        h.refresh_from_db()
        self.assertEqual(h.fluid_intake_ml, 2500.0)

    def test_hydration_delete_post(self):
        h = HydrationLog.objects.create(
            date=date(2026, 3, 1), fluid_intake_ml=2000,
        )
        response = self.client.post(reverse('hydration_delete', kwargs={'pk': h.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HydrationLog.objects.count(), 0)

    # ----- Energy -----
    def test_energy_add_post(self):
        response = self.client.post(reverse('energy_add'), {
            'date': '2026-03-01',
            'energy_score': '7',
            'notes': 'Feeling good',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EnergyFatigueLog.objects.count(), 1)

    def test_energy_edit_post(self):
        e = EnergyFatigueLog.objects.create(
            date=date(2026, 3, 1), energy_score=5,
        )
        response = self.client.post(reverse('energy_edit', kwargs={'pk': e.pk}), {
            'date': '2026-03-01',
            'energy_score': '8',
        })
        self.assertEqual(response.status_code, 302)
        e.refresh_from_db()
        self.assertEqual(e.energy_score, 8)

    def test_energy_delete_post(self):
        e = EnergyFatigueLog.objects.create(
            date=date(2026, 3, 1), energy_score=5,
        )
        response = self.client.post(reverse('energy_delete', kwargs={'pk': e.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EnergyFatigueLog.objects.count(), 0)

    # ----- Custom Vitals -----
    def test_custom_vital_define_post(self):
        response = self.client.post(reverse('custom_vital_define'), {
            'name': 'Grip Strength',
            'unit': 'kg',
            'normal_min': '30',
            'normal_max': '60',
            'description': 'Hand grip test',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CustomVitalDefinition.objects.count(), 1)

    def test_custom_vital_add_entry_post(self):
        defn = CustomVitalDefinition.objects.create(name="Grip Strength", unit="kg")
        response = self.client.post(reverse('custom_vital_add_entry'), {
            'date': '2026-03-01',
            'definition': str(defn.pk),
            'value': '45',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CustomVitalEntry.objects.count(), 1)

    def test_custom_vital_edit_entry_post(self):
        defn = CustomVitalDefinition.objects.create(name="Grip Strength", unit="kg")
        entry = CustomVitalEntry.objects.create(
            definition=defn, date=date(2026, 3, 1), value=45.0,
        )
        response = self.client.post(reverse('custom_vital_edit_entry', kwargs={'pk': entry.pk}), {
            'date': '2026-03-01',
            'value': '50',
        })
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.value, 50.0)

    def test_custom_vital_delete_entry_post(self):
        defn = CustomVitalDefinition.objects.create(name="Grip Strength", unit="kg")
        entry = CustomVitalEntry.objects.create(
            definition=defn, date=date(2026, 3, 1), value=45.0,
        )
        response = self.client.post(reverse('custom_vital_delete_entry', kwargs={'pk': entry.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CustomVitalEntry.objects.count(), 0)

    # ----- Pain -----
    def test_pain_add_post(self):
        response = self.client.post(reverse('pain_add'), {
            'date': '2026-03-01',
            'body_region': 'lower_back',
            'pain_level': '6',
            'description': 'Dull ache',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PainLog.objects.count(), 1)

    def test_pain_edit_post(self):
        p = PainLog.objects.create(
            date=date(2026, 3, 1), body_region='lower_back', pain_level=6,
        )
        response = self.client.post(reverse('pain_edit', kwargs={'pk': p.pk}), {
            'date': '2026-03-01',
            'body_region': 'neck',
            'pain_level': '4',
        })
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.body_region, 'neck')
        self.assertEqual(p.pain_level, 4)

    def test_pain_delete_post(self):
        p = PainLog.objects.create(
            date=date(2026, 3, 1), body_region='lower_back', pain_level=6,
        )
        response = self.client.post(reverse('pain_delete', kwargs={'pk': p.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PainLog.objects.count(), 0)

    # ----- RMR -----
    def test_rmr_add_post(self):
        response = self.client.post(reverse('rmr_add'), {
            'date': '2026-03-01',
            'age': '30',
            'weight_kg': '80',
            'height_cm': '180',
            'gender': 'M',
            'formula': 'mifflin',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RestingMetabolicRate.objects.count(), 1)
        rmr = RestingMetabolicRate.objects.first()
        self.assertIsNotNone(rmr.rmr_value)

    def test_rmr_edit_post(self):
        rmr = RestingMetabolicRate.objects.create(
            date=date(2026, 3, 1), age=30, weight_kg=80,
            height_cm=180, gender='M', formula='mifflin',
        )
        response = self.client.post(reverse('rmr_edit', kwargs={'pk': rmr.pk}), {
            'date': '2026-03-01',
            'age': '31',
            'weight_kg': '82',
            'height_cm': '180',
            'gender': 'M',
            'formula': 'harris',
        })
        self.assertEqual(response.status_code, 302)
        rmr.refresh_from_db()
        self.assertEqual(rmr.age, 31)
        self.assertEqual(rmr.formula, 'harris')

    def test_rmr_delete_post(self):
        rmr = RestingMetabolicRate.objects.create(
            date=date(2026, 3, 1), age=30, weight_kg=80,
            height_cm=180, gender='M', formula='mifflin',
        )
        response = self.client.post(reverse('rmr_delete', kwargs={'pk': rmr.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RestingMetabolicRate.objects.count(), 0)

    # ----- Orthostatic -----
    def test_orthostatic_add_post(self):
        response = self.client.post(reverse('orthostatic_add'), {
            'date': '2026-03-01',
            'supine_hr': '60',
            'standing_hr': '85',
            'supine_systolic': '120',
            'supine_diastolic': '80',
            'standing_systolic': '110',
            'standing_diastolic': '75',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OrthostaticReading.objects.count(), 1)

    def test_orthostatic_edit_post(self):
        o = OrthostaticReading.objects.create(
            date=date(2026, 3, 1), supine_hr=60, standing_hr=85,
        )
        response = self.client.post(reverse('orthostatic_edit', kwargs={'pk': o.pk}), {
            'date': '2026-03-02',
            'supine_hr': '62',
            'standing_hr': '90',
        })
        self.assertEqual(response.status_code, 302)
        o.refresh_from_db()
        self.assertEqual(o.supine_hr, 62)
        self.assertEqual(o.standing_hr, 90)

    def test_orthostatic_delete_post(self):
        o = OrthostaticReading.objects.create(
            date=date(2026, 3, 1), supine_hr=60, standing_hr=85,
        )
        response = self.client.post(reverse('orthostatic_delete', kwargs={'pk': o.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OrthostaticReading.objects.count(), 0)

    # ----- Reproductive -----
    def test_reproductive_add_post(self):
        response = self.client.post(reverse('reproductive_add'), {
            'date': '2026-03-01',
            'cycle_day': '14',
            'phase': 'ovulation',
            'flow_intensity': '0',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReproductiveHealthLog.objects.count(), 1)

    def test_reproductive_edit_post(self):
        r = ReproductiveHealthLog.objects.create(
            date=date(2026, 3, 1), cycle_day=14, phase='ovulation',
        )
        response = self.client.post(reverse('reproductive_edit', kwargs={'pk': r.pk}), {
            'date': '2026-03-01',
            'cycle_day': '15',
            'phase': 'luteal',
        })
        self.assertEqual(response.status_code, 302)
        r.refresh_from_db()
        self.assertEqual(r.cycle_day, 15)
        self.assertEqual(r.phase, 'luteal')

    def test_reproductive_delete_post(self):
        r = ReproductiveHealthLog.objects.create(
            date=date(2026, 3, 1), cycle_day=14, phase='ovulation',
        )
        response = self.client.post(reverse('reproductive_delete', kwargs={'pk': r.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReproductiveHealthLog.objects.count(), 0)

    # ----- Symptom -----
    def test_symptom_add_post(self):
        response = self.client.post(reverse('symptom_add'), {
            'date': '2026-03-01',
            'symptom': 'Headache',
            'severity': '3',
            'duration': '2 hours',
            'notes': 'After screen time',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SymptomJournal.objects.count(), 1)

    def test_symptom_edit_post(self):
        s = SymptomJournal.objects.create(
            date=date(2026, 3, 1), symptom='Headache', severity=3,
        )
        response = self.client.post(reverse('symptom_edit', kwargs={'pk': s.pk}), {
            'date': '2026-03-01',
            'symptom': 'Migraine',
            'severity': '4',
        })
        self.assertEqual(response.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.symptom, 'Migraine')
        self.assertEqual(s.severity, 4)

    def test_symptom_delete_post(self):
        s = SymptomJournal.objects.create(
            date=date(2026, 3, 1), symptom='Headache', severity=3,
        )
        response = self.client.post(reverse('symptom_delete', kwargs={'pk': s.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SymptomJournal.objects.count(), 0)

    # ----- Metabolic -----
    def test_metabolic_add_post(self):
        response = self.client.post(reverse('metabolic_add'), {
            'date': '2026-03-01',
            'blood_glucose': '95',
            'insulin_level': '10',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MetabolicLog.objects.count(), 1)

    def test_metabolic_edit_post(self):
        m = MetabolicLog.objects.create(
            date=date(2026, 3, 1), blood_glucose=95.0,
        )
        response = self.client.post(reverse('metabolic_edit', kwargs={'pk': m.pk}), {
            'date': '2026-03-01',
            'blood_glucose': '100',
            'insulin_level': '12',
        })
        self.assertEqual(response.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.blood_glucose, 100.0)

    def test_metabolic_delete_post(self):
        m = MetabolicLog.objects.create(
            date=date(2026, 3, 1), blood_glucose=95.0,
        )
        response = self.client.post(reverse('metabolic_delete', kwargs={'pk': m.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MetabolicLog.objects.count(), 0)

    # ----- Ketone -----
    def test_ketone_add_post(self):
        response = self.client.post(reverse('ketone_add'), {
            'date': '2026-03-01',
            'value': '0.8',
            'measurement_type': 'blood',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(KetoneLog.objects.count(), 1)

    def test_ketone_edit_post(self):
        k = KetoneLog.objects.create(
            date=date(2026, 3, 1), value=0.8, measurement_type='blood',
        )
        response = self.client.post(reverse('ketone_edit', kwargs={'pk': k.pk}), {
            'date': '2026-03-01',
            'value': '1.2',
            'measurement_type': 'urine',
        })
        self.assertEqual(response.status_code, 302)
        k.refresh_from_db()
        self.assertEqual(k.value, 1.2)
        self.assertEqual(k.measurement_type, 'urine')

    def test_ketone_delete_post(self):
        k = KetoneLog.objects.create(
            date=date(2026, 3, 1), value=0.8, measurement_type='blood',
        )
        response = self.client.post(reverse('ketone_delete', kwargs={'pk': k.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(KetoneLog.objects.count(), 0)


class Phase2VitalsExtensionTests(TestCase):
    """Test the extended VitalSign model with BBT, SpO2, respiratory_rate."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

        self.vital = VitalSign.objects.create(
            date=date(2026, 3, 1), weight=70.0, heart_rate=72,
            systolic_bp=120, diastolic_bp=80,
            bbt=36.6, spo2=98.0, respiratory_rate=16,
        )

    def test_add_vitals_with_new_fields_post(self):
        response = self.client.post(reverse('add_vitals'), {
            'date': '2026-03-02',
            'weight': '72.0',
            'heart_rate': '70',
            'systolic_bp': '118',
            'diastolic_bp': '78',
            'bbt': '36.7',
            'spo2': '99',
            'respiratory_rate': '15',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VitalSign.objects.count(), 2)
        v = VitalSign.objects.order_by('-id').first()
        self.assertEqual(v.bbt, 36.7)
        self.assertEqual(v.spo2, 99.0)
        self.assertEqual(v.respiratory_rate, 15)

    def test_edit_vitals_with_new_fields_post(self):
        response = self.client.post(
            reverse('edit_vitals', kwargs={'vital_id': self.vital.id}), {
                'date': '2026-03-01',
                'weight': '71.0',
                'heart_rate': '74',
                'systolic_bp': '122',
                'diastolic_bp': '82',
                'bbt': '36.8',
                'spo2': '97',
                'respiratory_rate': '18',
            })
        self.assertEqual(response.status_code, 302)
        self.vital.refresh_from_db()
        self.assertEqual(self.vital.bbt, 36.8)
        self.assertEqual(self.vital.spo2, 97.0)
        self.assertEqual(self.vital.respiratory_rate, 18)

    def test_vitals_list_shows_new_fields(self):
        response = self.client.get(reverse('vitals'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '36.6')
        self.assertContains(response, '98.0')
        self.assertContains(response, '16')

    def test_vitals_charts_context_has_new_fields(self):
        response = self.client.get(reverse('vitals_charts'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('bbt_data', response.context)
        self.assertIn('spo2_data', response.context)
        self.assertIn('rr_data', response.context)
        self.assertEqual(len(response.context['bbt_data']), 1)
        self.assertEqual(response.context['bbt_data'][0]['y'], 36.6)
        self.assertEqual(response.context['spo2_data'][0]['y'], 98.0)
        self.assertEqual(response.context['rr_data'][0]['y'], 16)
class AnnotationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        self.blood_test = BloodTest.objects.create(
            test_name="Hemoglobin", value=15.0, unit="g/dL",
            date=date(2026, 1, 15), normal_min=13.8, normal_max=17.2,
            category="Blood Count"
        )
        self.vital = VitalSign.objects.create(
            date=date(2026, 1, 15), weight=70.5, heart_rate=72,
            systolic_bp=120, diastolic_bp=80
        )

    def test_add_annotation_to_blood_test(self):
        response = self.client.post(
            reverse('add_annotation', kwargs={'model_type': 'blood_test', 'object_id': self.blood_test.id}),
            {'note': 'Feeling tired today', 'next': reverse('index')}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DataPointAnnotation.objects.count(), 1)
        annotation = DataPointAnnotation.objects.first()
        self.assertEqual(annotation.note, 'Feeling tired today')
        self.assertEqual(annotation.blood_test, self.blood_test)

    def test_add_annotation_to_vital_sign(self):
        response = self.client.post(
            reverse('add_annotation', kwargs={'model_type': 'vital_sign', 'object_id': self.vital.id}),
            {'note': 'After exercise', 'next': reverse('index')}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DataPointAnnotation.objects.count(), 1)
        annotation = DataPointAnnotation.objects.first()
        self.assertEqual(annotation.note, 'After exercise')
        self.assertEqual(annotation.vital_sign, self.vital)

    def test_add_empty_annotation_fails(self):
        response = self.client.post(
            reverse('add_annotation', kwargs={'model_type': 'blood_test', 'object_id': self.blood_test.id}),
            {'note': '', 'next': reverse('index')}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DataPointAnnotation.objects.count(), 0)

    def test_delete_annotation(self):
        annotation = DataPointAnnotation.objects.create(
            blood_test=self.blood_test, note='Test note'
        )
        response = self.client.post(
            reverse('delete_annotation', kwargs={'annotation_id': annotation.id}),
            {'next': reverse('index')}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DataPointAnnotation.objects.count(), 0)

    def test_chart_shows_annotations(self):
        DataPointAnnotation.objects.create(
            blood_test=self.blood_test, note='Important note'
        )
        response = self.client.get(reverse('chart', kwargs={'test_name': 'Hemoglobin'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Important note')


class BulkEditTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        self.test1 = BloodTest.objects.create(
            test_name="Hemoglobin", value=15.0, unit="g/dL",
            date=date(2026, 1, 15), normal_min=13.8, normal_max=17.2,
            category="Blood Count"
        )
        self.test2 = BloodTest.objects.create(
            test_name="WBC", value=7.5, unit="10^3/uL",
            date=date(2026, 1, 15), normal_min=4.5, normal_max=11.0,
            category="Blood Count"
        )

    def test_bulk_edit_page(self):
        response = self.client.get(reverse('bulk_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hemoglobin')
        self.assertContains(response, 'WBC')

    def test_bulk_edit_update(self):
        response = self.client.post(reverse('bulk_edit'), {
            'test_ids': [str(self.test1.id), str(self.test2.id)],
            f'value_{self.test1.id}': '14.0',
            f'date_{self.test1.id}': '2026-02-01',
            f'value_{self.test2.id}': '8.0',
            f'date_{self.test2.id}': '2026-02-01',
        })
        self.assertEqual(response.status_code, 302)
        self.test1.refresh_from_db()
        self.test2.refresh_from_db()
        self.assertEqual(self.test1.value, 14.0)
        self.assertEqual(self.test2.value, 8.0)

    def test_bulk_edit_delete(self):
        response = self.client.post(reverse('bulk_edit'), {
            'test_ids': [str(self.test1.id), str(self.test2.id)],
            'delete_ids': [str(self.test1.id)],
            f'value_{self.test2.id}': '7.5',
            f'date_{self.test2.id}': '2026-01-15',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloodTest.objects.count(), 1)
        self.assertEqual(BloodTest.objects.first().test_name, 'WBC')

    def test_bulk_edit_empty(self):
        BloodTest.objects.all().delete()
        response = self.client.get(reverse('bulk_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No blood test records to edit')


class DashboardWidgetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_customize_dashboard_page(self):
        response = self.client.get(reverse('customize_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customize Dashboard')

    def test_default_widgets_created(self):
        self.client.get(reverse('customize_dashboard'))
        self.assertEqual(DashboardWidget.objects.count(), 7)

    def test_update_widgets(self):
        self.client.get(reverse('customize_dashboard'))
        widgets = list(DashboardWidget.objects.all())
        data = {
            'widgets': [
                {'id': widgets[0].id, 'position': 5, 'visible': False},
                {'id': widgets[1].id, 'position': 0, 'visible': True},
            ]
        }
        response = self.client.post(
            reverse('update_widgets'),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        widgets[0].refresh_from_db()
        self.assertEqual(widgets[0].position, 5)
        self.assertFalse(widgets[0].visible)

    def test_update_widgets_invalid_json(self):
        response = self.client.post(
            reverse('update_widgets'),
            'not json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_update_widgets_get_rejected(self):
        response = self.client.get(reverse('update_widgets'))
        self.assertEqual(response.status_code, 405)

    def test_index_has_pdf_export(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export PDF')

    def test_index_has_customize_link(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customize')

    def test_index_has_bulk_edit_link(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bulk Edit')

    def test_widget_visibility_affects_dashboard(self):
        # First load creates default widgets
        self.client.get(reverse('index'))
        # Hide summary_cards widget
        widget = DashboardWidget.objects.get(widget_type='summary_cards')
        widget.visible = False
        widget.save()
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Total Tests Recorded')


class PDFExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_blood_charts_has_pdf_export(self):
        response = self.client.get(reverse('blood_tests_charts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export PDF')

    def test_vitals_charts_has_pdf_export(self):
        response = self.client.get(reverse('vitals_charts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export PDF')

    def test_comparative_bar_charts_has_pdf_export(self):
        response = self.client.get(reverse('comparative_bar_charts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export PDF')

    def test_boxplots_has_pdf_export(self):
        response = self.client.get(reverse('blood_tests_boxplots'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export PDF')

    def test_chart_detail_has_pdf_export(self):
        BloodTest.objects.create(
            test_name="Hemoglobin", value=15.0, unit="g/dL",
            date=date(2026, 1, 15), normal_min=13.8, normal_max=17.2,
            category="Blood Count"
        )
        response = self.client.get(reverse('chart', kwargs={'test_name': 'Hemoglobin'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export PDF')


class Phase3DarkModeTests(TestCase):
    """Dark mode toggle and theme infrastructure."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_base_template_has_dark_mode_toggle(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'dark-mode-toggle')

    def test_base_template_has_data_theme_attribute(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'data-theme=')

    def test_ui_css_loaded(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'css/ui.css')

    def test_ui_js_loaded(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'js/ui.js')


class Phase3NavigationTests(TestCase):
    """Sidebar navigation system."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_sidebar_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'sidebar')
        self.assertContains(response, 'sidebar-toggle')

    def test_sidebar_has_categories(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'sidebar-category')
        self.assertContains(response, 'Tracking')
        self.assertContains(response, 'Analytics')
        self.assertContains(response, 'Intelligence')
        self.assertContains(response, 'Settings')

    def test_sidebar_has_all_nav_links(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Vitals')
        self.assertContains(response, 'History')
        self.assertContains(response, 'Body Composition')
        self.assertContains(response, 'Hydration')
        self.assertContains(response, 'Pain Mapping')


class Phase3AccessibilityTests(TestCase):
    """WCAG 2.1 AA compliance features."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_skip_to_content_link(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'skip-to-content')
        self.assertContains(response, 'Skip to main content')

    def test_main_content_landmark(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'role="main"')

    def test_nav_has_aria_label(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'aria-label="Main navigation"')

    def test_buttons_have_aria_labels(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'aria-label="Toggle dark mode"')
        self.assertContains(response, 'aria-label="Toggle navigation"')

    def test_lang_attribute_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'lang="en"')

    def test_search_has_role(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'role="search"')


class Phase3QuickEntryTests(TestCase):
    """Quick-entry vitals modal."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_quick_entry_button_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'quick-entry-btn')

    def test_quick_entry_modal_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'quickEntryModal')
        self.assertContains(response, 'Quick Vital Sign Entry')

    def test_quick_entry_modal_has_fields(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'qe-weight')
        self.assertContains(response, 'qe-hr')
        self.assertContains(response, 'qe-systolic')
        self.assertContains(response, 'qe-diastolic')
        self.assertContains(response, 'qe-spo2')


class Phase3PWATests(TestCase):
    """Progressive Web App features."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_manifest_link_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'manifest.json')

    def test_theme_color_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'theme-color')

    def test_service_worker_js_registered(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'js/ui.js')


class Phase3GlobalSearchTests(TestCase):
    """Global search API."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

        BloodTest.objects.create(
            test_name="Hemoglobin", value=15.0, unit="g/dL",
            date=date(2026, 1, 15), normal_min=13.8, normal_max=17.2,
            category="Blood Count"
        )

    def test_search_api_endpoint_exists(self):
        response = self.client.get(reverse('global_search'), {'q': 'hemo'})
        self.assertEqual(response.status_code, 200)

    def test_search_returns_json(self):
        response = self.client.get(reverse('global_search'), {'q': 'hemo'})
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertIn('results', data)

    def test_search_finds_blood_test(self):
        response = self.client.get(reverse('global_search'), {'q': 'Hemoglobin'})
        data = json.loads(response.content)
        self.assertTrue(len(data['results']) > 0)
        self.assertEqual(data['results'][0]['type'], 'blood_test')
        self.assertEqual(data['results'][0]['name'], 'Hemoglobin')

    def test_search_short_query_returns_empty(self):
        response = self.client.get(reverse('global_search'), {'q': 'a'})
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 0)

    def test_search_empty_query_returns_empty(self):
        response = self.client.get(reverse('global_search'), {'q': ''})
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 0)

    def test_search_no_match(self):
        response = self.client.get(reverse('global_search'), {'q': 'zzzznonexistent'})
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 0)

    def test_search_input_in_template(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'global-search-input')


class Phase3MedicalTooltipTests(TestCase):
    """Medical tooltips on forms and labels."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_tooltips_on_quick_entry(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'data-medical-tooltip')

    def test_tooltip_content_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Blood oxygen saturation')
        self.assertContains(response, 'Resting heart rate')


class Phase3VoiceInputTests(TestCase):
    """Voice-to-text integration."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_voice_button_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'voice-input-btn')

    def test_voice_button_has_aria(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'aria-label="Voice search"')


class Phase3OnboardingTests(TestCase):
    """Onboarding tour button."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')


    def test_tour_button_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'start-tour-btn')

    def test_tour_button_has_label(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Start guided tour')


# ============================================================================
# User Authentication and Profile Tests
# ============================================================================

class Phase4RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create your account')

    def test_register_success(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'SecureP@ss123!',
            'password2': 'SecureP@ss123!',
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(User.objects.filter(username='newuser').exists())
        # Profile should be auto-created
        user = User.objects.get(username='newuser')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertTrue(PrivacyPreference.objects.filter(user=user).exists())

    def test_register_creates_security_log(self):
        self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'SecureP@ss123!',
            'password2': 'SecureP@ss123!',
        })
        user = User.objects.get(username='newuser')
        self.assertTrue(SecurityLog.objects.filter(user=user, action='login').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user('existing', 'existing@test.com', 'pass123')
        response = self.client.post(reverse('register'), {
            'username': 'existing',
            'email': 'new@test.com',
            'password1': 'SecureP@ss123!',
            'password2': 'SecureP@ss123!',
        })
        self.assertEqual(response.status_code, 200)  # Re-renders form with errors
        self.assertEqual(User.objects.filter(username='existing').count(), 1)

    def test_register_redirects_authenticated(self):
        User.objects.create_user('testuser', 'test@test.com', 'pass123')
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 302)


class Phase4LoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in to your account')

    def test_login_success(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_creates_security_log(self):
        self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertTrue(SecurityLog.objects.filter(user=self.user, action='login').exists())

    def test_login_failure_logs_event(self):
        self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertTrue(SecurityLog.objects.filter(user=self.user, action='login_failed').exists())

    def test_login_redirects_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 302)

    def test_login_timeout_message(self):
        response = self.client.get(reverse('login') + '?timeout=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'timed out')


class SocialLoginURLTests(TestCase):
    """Test that social login buttons link to proper OAuth URLs."""

    def setUp(self):
        self.client = Client()

    def test_login_page_has_google_oauth_url(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, '/accounts/social/google/login/')

    def test_login_page_has_microsoft_oauth_url(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, '/accounts/social/microsoft/login/')

    def test_login_page_has_apple_oauth_url(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, '/accounts/social/apple/login/')

    def test_register_page_has_google_oauth_url(self):
        response = self.client.get(reverse('register'))
        self.assertContains(response, '/accounts/social/google/login/')

    def test_register_page_has_microsoft_oauth_url(self):
        response = self.client.get(reverse('register'))
        self.assertContains(response, '/accounts/social/microsoft/login/')

    def test_register_page_has_apple_oauth_url(self):
        response = self.client.get(reverse('register'))
        self.assertContains(response, '/accounts/social/apple/login/')


class Phase4LogoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_logout(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    def test_logout_creates_security_log(self):
        self.client.get(reverse('logout'))
        self.assertTrue(SecurityLog.objects.filter(user=self.user, action='logout').exists())


class Phase4ProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_profile_page_loads(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        response = self.client.post(reverse('profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'updated@example.com',
            'biological_sex': 'male',
            'height_cm': '175.5',
            'theme_preference': 'dark',
            'genetic_baseline_info': 'Some info',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.email, 'updated@example.com')
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.biological_sex, 'male')
        self.assertEqual(profile.height_cm, 175.5)

    def test_profile_update_logs_event(self):
        self.client.post(reverse('profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'theme_preference': 'system',
        })
        self.assertTrue(SecurityLog.objects.filter(user=self.user, action='profile_updated').exists())

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)


class Phase4PasswordChangeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_change_password_page_loads(self):
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 200)

    def test_change_password_success(self):
        response = self.client.post(reverse('change_password'), {
            'old_password': 'testpass123',
            'new_password1': 'NewSecureP@ss456!',
            'new_password2': 'NewSecureP@ss456!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SecurityLog.objects.filter(user=self.user, action='password_changed').exists())


class Phase4SecurityLogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_security_log_page_loads(self):
        response = self.client.get(reverse('security_log'))
        self.assertEqual(response.status_code, 200)

    def test_security_log_shows_events(self):
        SecurityLog.objects.create(
            user=self.user, action='login',
            ip_address='192.168.1.1', device_type='Desktop'
        )
        response = self.client.get(reverse('security_log'))
        self.assertContains(response, '192.168.1.1')
        self.assertContains(response, 'Desktop')


class Phase4SessionManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_sessions_page_loads(self):
        response = self.client.get(reverse('active_sessions'))
        self.assertEqual(response.status_code, 200)

    def test_terminate_session(self):
        session = UserSession.objects.create(
            user=self.user,
            session_key='test-session-key-123',
            ip_address='10.0.0.1',
            is_active=True,
        )
        response = self.client.post(reverse('terminate_session', args=[session.pk]))
        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertFalse(session.is_active)


class Phase4PrivacyPreferencesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_privacy_page_loads(self):
        response = self.client.get(reverse('privacy_preferences'))
        self.assertEqual(response.status_code, 200)

    def test_privacy_update(self):
        response = self.client.post(reverse('privacy_preferences'), {
            'allow_data_sharing': True,
            'allow_analytics': False,
            'allow_research_use': False,
            'data_retention_days': 180,
            'show_profile_publicly': False,
        })
        self.assertEqual(response.status_code, 302)
        prefs = PrivacyPreference.objects.get(user=self.user)
        self.assertTrue(prefs.allow_data_sharing)
        self.assertEqual(prefs.data_retention_days, 180)


class Phase4AccountDeletionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='deleteuser', password='testpass123', email='delete@example.com'
        )
        UserProfile.objects.create(user=self.user)
        self.client.login(username='deleteuser', password='testpass123')

    def test_delete_page_loads(self):
        response = self.client.get(reverse('delete_account'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DELETE')

    def test_delete_account_success(self):
        response = self.client.post(reverse('delete_account'), {
            'confirm_text': 'DELETE',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='deleteuser').exists())

    def test_delete_account_wrong_confirmation(self):
        response = self.client.post(reverse('delete_account'), {
            'confirm_text': 'WRONG',
        })
        self.assertEqual(response.status_code, 200)  # Re-renders form
        self.assertTrue(User.objects.filter(username='deleteuser').exists())


class Phase4MFATests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_mfa_setup_page_loads(self):
        response = self.client.get(reverse('mfa_setup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'svg')  # QR code

    def test_mfa_disable_page_loads(self):
        response = self.client.get(reverse('mfa_disable'))
        self.assertEqual(response.status_code, 200)

    def test_mfa_verify_redirects_without_session(self):
        response = self.client.get(reverse('mfa_verify'))
        self.assertEqual(response.status_code, 302)

    def test_mfa_setup_creates_device(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        self.client.get(reverse('mfa_setup'))
        self.assertTrue(TOTPDevice.objects.filter(user=self.user).exists())


class Phase4ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )

    def test_user_profile_creation(self):
        profile = UserProfile.objects.create(user=self.user, biological_sex='female', height_cm=165.0)
        self.assertEqual(str(profile), 'Profile of testuser')

    def test_security_log_creation(self):
        log = SecurityLog.objects.create(
            user=self.user, action='login',
            ip_address='127.0.0.1', device_type='Desktop'
        )
        self.assertIn('testuser', str(log))
        self.assertIn('login', str(log))

    def test_user_session_creation(self):
        session = UserSession.objects.create(
            user=self.user, session_key='abc123',
            ip_address='192.168.1.1'
        )
        self.assertIn('testuser', str(session))

    def test_privacy_preference_creation(self):
        pref = PrivacyPreference.objects.create(user=self.user)
        self.assertFalse(pref.allow_data_sharing)
        self.assertEqual(pref.data_retention_days, 365)
        self.assertIn('testuser', str(pref))

    def test_security_log_ordering(self):
        SecurityLog.objects.create(user=self.user, action='login')
        SecurityLog.objects.create(user=self.user, action='logout')
        logs = SecurityLog.objects.filter(user=self.user)
        # Most recent first
        self.assertEqual(logs[0].action, 'logout')


class Phase4ProtectedViewTests(TestCase):
    """Ensure views redirect to login when not authenticated."""
    def setUp(self):
        self.client = Client()

    def test_index_requires_login(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_history_requires_login(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_vitals_requires_login(self):
        response = self.client.get(reverse('vitals'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_security_log_requires_login(self):
        response = self.client.get(reverse('security_log'))
        self.assertEqual(response.status_code, 302)


class Phase4SidebarTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_sidebar_has_account_section(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Account')
        self.assertContains(response, 'Profile')
        self.assertContains(response, 'Security Log')
        self.assertContains(response, 'Sessions')
        self.assertContains(response, 'Privacy')
        self.assertContains(response, 'Logout')


class DynamicSidebarTests(TestCase):
    """Tests for the dynamic sidebar context processor."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_sidebar_context_processor_provides_sidebar_nav(self):
        response = self.client.get(reverse('index'))
        self.assertIn('sidebar_nav', response.context)
        self.assertIsInstance(response.context['sidebar_nav'], list)
        self.assertTrue(len(response.context['sidebar_nav']) > 0)

    def test_sidebar_has_all_categories(self):
        response = self.client.get(reverse('index'))
        expected = [
            'Overview', 'Analytics', 'Tracking',
            'Sleep &amp; Nutrition', 'Intelligence',
            'Devices', 'Sharing',
            'Settings', 'Administration',
        ]
        for cat in expected:
            self.assertContains(response, cat)

    def test_sidebar_has_new_phase5_features(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Wearable Devices')
        self.assertContains(response, 'Sync Logs')

    def test_sidebar_has_new_phase6_features(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Sleep Tracking')
        self.assertContains(response, 'Circadian Rhythm')
        self.assertContains(response, 'Dream Journal')
        self.assertContains(response, 'Macronutrients')
        self.assertContains(response, 'Micronutrients')
        self.assertContains(response, 'Food Entries')
        self.assertContains(response, 'Fasting')
        self.assertContains(response, 'Caffeine &amp; Alcohol')

    def test_sidebar_has_new_phase7_features(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Audit Logs')
        self.assertContains(response, 'Encryption Keys')
        self.assertContains(response, 'Tenant Config')
        self.assertContains(response, 'Backup Config')

    def test_sidebar_has_new_phase8_features(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Medications')
        self.assertContains(response, 'Health Goals')
        self.assertContains(response, 'Critical Alerts')
        self.assertContains(response, 'Health Reports')
        self.assertContains(response, 'Biological Age')
        self.assertContains(response, 'Predictive Biomarkers')

    def test_sidebar_has_new_phase9_features(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Secure Links')
        self.assertContains(response, 'Practitioner Access')
        self.assertContains(response, 'Intake Summaries')
        self.assertContains(response, 'Data Exports')
        self.assertContains(response, 'Stakeholder Emails')

    def test_sidebar_has_integration_features(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Integration Config')
        self.assertContains(response, 'Integration Sub-tasks')

    def test_sidebar_active_state_on_dashboard(self):
        response = self.client.get(reverse('index'))
        content = response.content.decode()
        self.assertIn('active', content)

    def test_sidebar_context_processor_items_have_urls(self):
        response = self.client.get(reverse('index'))
        nav = response.context['sidebar_nav']
        for section in nav:
            for item in section['items']:
                self.assertTrue(item['url'].startswith('/'))


# ===== Model Tests =====

from tracker.models import (
    WearableDevice, WearableSyncLog, WEARABLE_PLATFORMS,
    SleepLog, CircadianRhythmLog, DreamJournal, MacronutrientLog,
    MicronutrientLog, FoodEntry, FastingLog, CaffeineAlcoholLog,
    UserProfile, FamilyAccount, EncryptionKey, AuditLog,
    APIRateLimitConfig, ConsentLog, TenantConfig, AdminTelemetry,
    AnonymizedDataReport, DatabaseScalingConfig, BackupConfiguration,
    PredictiveBiomarker, HealthReport, ClinicalTrialMatch,
    BiologicalAgeCalculation, MedicationSchedule, PharmacologicalInteraction,
    HealthGoal, CriticalAlert,
    SecureViewingLink, PractitionerAccess, IntakeSummary,
    DataExportRequest, StakeholderEmail,
    IntegrationConfig, IntegrationSubTask,
    INTEGRATION_CATEGORIES, INTEGRATION_FEATURE_TYPES,
)


class Phase5ModelTests(TestCase):
    """Test model creation, __str__, and defaults for these models."""

    def test_wearable_device_str(self):
        d = WearableDevice.objects.create(platform='fitbit', device_name='Charge 5')
        self.assertIn('Fitbit', str(d))

    def test_wearable_device_default_active(self):
        d = WearableDevice.objects.create(platform='fitbit', device_name='Charge 5')
        self.assertTrue(d.is_active)

    def test_sync_log_str(self):
        d = WearableDevice.objects.create(platform='fitbit', device_name='Charge 5')
        sl = WearableSyncLog.objects.create(device=d, status='success')
        self.assertIn('success', str(sl))

    def test_wearable_device_new_fields(self):
        """Test the new OAuth fields on WearableDevice."""
        user = User.objects.create_user(username='oauthuser', password='testpass123')
        d = WearableDevice.objects.create(
            user=user,
            platform='withings',
            device_name='Body+',
            access_token='test_token',
            refresh_token='test_refresh',
            token_expires_at=timezone.now(),
            scope='user.metrics user.activity',
        )
        self.assertEqual(d.user, user)
        self.assertEqual(d.scope, 'user.metrics user.activity')
        self.assertIsNotNone(d.token_expires_at)


class Phase5IntegrationRegistryTests(TestCase):
    """Test the integration registry and client lookup."""

    def test_get_client_for_known_platforms(self):
        from tracker.integrations.registry import get_client
        for platform in ['withings', 'google_fit', 'fitbit', 'oura', 'strava',
                         'garmin', 'dexcom_cgm', 'samsung_health']:
            client = get_client(platform)
            self.assertIsNotNone(client, f"No client for {platform}")
            self.assertEqual(client.PLATFORM, platform)

    def test_get_client_returns_none_for_unknown(self):
        from tracker.integrations.registry import get_client
        self.assertIsNone(get_client('unknown_platform'))

    def test_get_client_returns_none_for_apple_health(self):
        from tracker.integrations.registry import get_client
        self.assertIsNone(get_client('apple_health'))

    def test_is_oauth_platform(self):
        from tracker.integrations.registry import is_oauth_platform
        self.assertTrue(is_oauth_platform('withings'))
        self.assertTrue(is_oauth_platform('google_fit'))
        self.assertTrue(is_oauth_platform('fitbit'))
        self.assertFalse(is_oauth_platform('apple_health'))
        self.assertFalse(is_oauth_platform('unknown'))


class Phase5OAuthClientTests(TestCase):
    """Test OAuth client methods."""

    def test_get_authorization_url_contains_params(self):
        from tracker.integrations.registry import get_client
        client = get_client('withings')
        url = client.get_authorization_url('http://localhost/callback', state='test123')
        self.assertIn('response_type=code', url)
        self.assertIn('state=test123', url)
        self.assertIn('redirect_uri=', url)

    def test_get_authorization_url_google_fit_offline(self):
        from tracker.integrations.registry import get_client
        client = get_client('google_fit')
        url = client.get_authorization_url('http://localhost/callback', state='abc')
        self.assertIn('access_type=offline', url)
        self.assertIn('prompt=consent', url)

    def test_oauth_config_has_required_fields(self):
        from tracker.integrations.registry import get_client
        for platform in ['withings', 'google_fit', 'fitbit', 'oura', 'strava',
                         'dexcom_cgm', 'samsung_health']:
            client = get_client(platform)
            config = client.get_oauth_config()
            self.assertTrue(config.authorize_url, f"No authorize_url for {platform}")
            self.assertTrue(config.token_url, f"No token_url for {platform}")
            self.assertTrue(config.api_base_url, f"No api_base_url for {platform}")


class Phase5IntegrationViewTests(TestCase):
    """Test integration views for connect, disconnect, sync."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='integrationuser', password='testpass123')
        self.client.login(username='integrationuser', password='testpass123')

    def test_wearable_device_list_shows_status(self):
        WearableDevice.objects.create(platform='fitbit', device_name='Charge 5')
        response = self.client.get(reverse('wearable_device_list'))
        self.assertEqual(response.status_code, 200)

    def test_wearable_connect_requires_login(self):
        device = WearableDevice.objects.create(platform='fitbit', device_name='Charge 5')
        self.client.logout()
        response = self.client.get(reverse('wearable_connect', kwargs={'pk': device.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_wearable_connect_no_credentials_shows_error(self):
        device = WearableDevice.objects.create(platform='fitbit', device_name='Charge 5')
        response = self.client.get(reverse('wearable_connect', kwargs={'pk': device.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        # Should show error about credentials not configured
        messages_list = list(response.context['messages'])
        self.assertTrue(any('not configured' in str(m) for m in messages_list))

    def test_wearable_disconnect(self):
        device = WearableDevice.objects.create(
            platform='fitbit', device_name='Charge 5',
            access_token='test_token', refresh_token='test_refresh',
        )
        response = self.client.post(
            reverse('wearable_disconnect', kwargs={'pk': device.pk}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.access_token, '')
        self.assertEqual(device.refresh_token, '')

    def test_wearable_sync_without_token_shows_error(self):
        device = WearableDevice.objects.create(platform='fitbit', device_name='Charge 5')
        response = self.client.post(
            reverse('wearable_sync', kwargs={'pk': device.pk}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(any('not connected' in str(m).lower() for m in messages_list))

    def test_wearable_callback_no_code_shows_error(self):
        response = self.client.get(
            reverse('wearable_oauth_callback', kwargs={'platform': 'fitbit'}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(any('no code' in str(m).lower() for m in messages_list))

    def test_new_url_patterns_resolve(self):
        """Verify the new URL patterns are accessible."""
        device = WearableDevice.objects.create(platform='fitbit', device_name='Test')
        # connect URL
        url = reverse('wearable_connect', kwargs={'pk': device.pk})
        self.assertIn('/wearables/connect/', url)
        # callback URL
        url = reverse('wearable_oauth_callback', kwargs={'platform': 'fitbit'})
        self.assertIn('/wearables/callback/fitbit/', url)
        # disconnect URL
        url = reverse('wearable_disconnect', kwargs={'pk': device.pk})
        self.assertIn('/wearables/disconnect/', url)
        # sync URL
        url = reverse('wearable_sync', kwargs={'pk': device.pk})
        self.assertIn('/wearables/sync/', url)


from unittest.mock import patch, MagicMock
from django.utils import timezone


class Phase5SyncDataTests(TestCase):
    """Test the sync_data flow with mocked API responses."""

    def test_sync_data_creates_log_on_success(self):
        from tracker.integrations.base import BaseOAuthClient
        device = WearableDevice.objects.create(
            platform='fitbit', device_name='Test',
            access_token='token', refresh_token='refresh',
        )

        class MockClient(BaseOAuthClient):
            PLATFORM = 'fitbit'
            def get_oauth_config(self):
                from tracker.integrations.base import OAuthConfig
                return OAuthConfig('Fitbit', 'id', 'secret',
                                   'http://auth', 'http://token', 'http://api')
            def fetch_data(self, device, start_date, end_date):
                return 5

        client = MockClient()
        sync_log = client.sync_data(device)
        self.assertEqual(sync_log.status, 'success')
        self.assertEqual(sync_log.records_synced, 5)
        self.assertIsNotNone(sync_log.completed_at)
        device.refresh_from_db()
        self.assertIsNotNone(device.last_synced)

    def test_sync_data_creates_log_on_failure(self):
        from tracker.integrations.base import BaseOAuthClient
        device = WearableDevice.objects.create(
            platform='fitbit', device_name='Test',
            access_token='token', refresh_token='refresh',
        )

        class MockClient(BaseOAuthClient):
            PLATFORM = 'fitbit'
            def get_oauth_config(self):
                from tracker.integrations.base import OAuthConfig
                return OAuthConfig('Fitbit', 'id', 'secret',
                                   'http://auth', 'http://token', 'http://api')
            def fetch_data(self, device, start_date, end_date):
                raise ConnectionError("API unreachable")

        client = MockClient()
        sync_log = client.sync_data(device)
        self.assertEqual(sync_log.status, 'failed')
        self.assertIn('API unreachable', sync_log.error_message)
        self.assertIsNotNone(sync_log.completed_at)


class Phase6ModelTests(TestCase):
    """Test model creation, __str__, and calculated fields for these models."""

    def test_sleep_log_str(self):
        s = SleepLog.objects.create(date=date(2026, 3, 1))
        self.assertIn('2026-03-01', str(s))

    def test_sleep_efficiency(self):
        s = SleepLog.objects.create(
            date=date(2026, 3, 1), total_sleep_minutes=420, awake_minutes=30,
        )
        self.assertEqual(s.sleep_efficiency, round(420 / 450 * 100, 1))

    def test_sleep_efficiency_none(self):
        s = SleepLog.objects.create(date=date(2026, 3, 1))
        self.assertIsNone(s.sleep_efficiency)

    def test_circadian_str(self):
        c = CircadianRhythmLog.objects.create(date=date(2026, 3, 1))
        self.assertIn('2026-03-01', str(c))

    def test_dream_journal_str(self):
        d = DreamJournal.objects.create(date=date(2026, 3, 1))
        self.assertIn('2026-03-01', str(d))

    def test_macronutrient_total_macros(self):
        m = MacronutrientLog.objects.create(
            date=date(2026, 3, 1), protein_grams=50, carbohydrate_grams=200, fat_grams=70,
        )
        self.assertEqual(m.total_macros_grams, 320.0)

    def test_macronutrient_str(self):
        m = MacronutrientLog.objects.create(date=date(2026, 3, 1))
        self.assertIn('Macros', str(m))

    def test_micronutrient_str(self):
        m = MicronutrientLog.objects.create(
            date=date(2026, 3, 1), nutrient_name='Vitamin D', amount=1000, unit='IU',
        )
        self.assertIn('Vitamin D', str(m))

    def test_food_entry_str(self):
        f = FoodEntry.objects.create(date=date(2026, 3, 1), food_name='Apple')
        self.assertIn('Apple', str(f))

    def test_fasting_goal_met_true(self):
        f = FastingLog.objects.create(
            date=date(2026, 3, 1), actual_hours=16, target_hours=16,
        )
        self.assertTrue(f.goal_met)

    def test_fasting_goal_met_false(self):
        f = FastingLog.objects.create(
            date=date(2026, 3, 1), actual_hours=12, target_hours=16,
        )
        self.assertFalse(f.goal_met)

    def test_fasting_goal_met_none(self):
        f = FastingLog.objects.create(date=date(2026, 3, 1))
        self.assertIsNone(f.goal_met)

    def test_caffeine_alcohol_str(self):
        c = CaffeineAlcoholLog.objects.create(date=date(2026, 3, 1), substance='caffeine')
        self.assertIn('Caffeine', str(c))

    def test_calculate_quality_score_full(self):
        s = SleepLog.objects.create(
            date=date(2026, 3, 1), total_sleep_minutes=420,
            rem_minutes=105, deep_sleep_minutes=84, awake_minutes=30,
        )
        score = s.calculate_quality_score()
        self.assertIsNotNone(score)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_calculate_quality_score_none(self):
        s = SleepLog.objects.create(date=date(2026, 3, 1))
        self.assertIsNone(s.calculate_quality_score())

    def test_calculate_quality_score_zero_total(self):
        s = SleepLog.objects.create(date=date(2026, 3, 1), total_sleep_minutes=0)
        self.assertIsNone(s.calculate_quality_score())

    def test_sleep_trend_insufficient_data(self):
        s = SleepLog.objects.create(date=date(2026, 3, 1), total_sleep_minutes=420, awake_minutes=30)
        self.assertIsNone(s.sleep_trend)

    def test_optimal_sleep_window_with_data(self):
        from datetime import time
        CircadianRhythmLog.objects.create(
            date=date(2026, 2, 25), sleep_onset=time(23, 0), wake_time=time(7, 0),
        )
        CircadianRhythmLog.objects.create(
            date=date(2026, 2, 26), sleep_onset=time(23, 30), wake_time=time(7, 30),
        )
        c = CircadianRhythmLog.objects.create(date=date(2026, 2, 27))
        window = c.optimal_sleep_window
        self.assertIsNotNone(window)
        self.assertIn('suggested_bedtime', window)
        self.assertIn('suggested_wake_time', window)

    def test_optimal_sleep_window_no_data(self):
        c = CircadianRhythmLog.objects.create(date=date(2026, 3, 1))
        # No entries with sleep_onset and wake_time
        self.assertIsNone(c.optimal_sleep_window)

    def test_micronutrient_deficiency_risk_field(self):
        m = MicronutrientLog.objects.create(
            date=date(2026, 3, 1), nutrient_name='Vitamin D', amount=400, unit='IU',
            deficiency_risk='high',
        )
        self.assertEqual(m.deficiency_risk, 'high')

    def test_food_entry_database_id_field(self):
        f = FoodEntry.objects.create(
            date=date(2026, 3, 1), food_name='Apple',
            food_database_id='usda:171688', source='usda',
        )
        self.assertEqual(f.food_database_id, 'usda:171688')
        self.assertEqual(f.source, 'usda')


class Phase7ModelTests(TestCase):
    """Test model creation and __str__ for these models."""

    def test_user_profile_role(self):
        user = User.objects.create_user(username='testuser', password='pass')
        p = UserProfile.objects.create(user=user, role='admin')
        self.assertIn('testuser', str(p))
        self.assertEqual(p.role, 'admin')

    def test_family_account_str(self):
        user = User.objects.create_user(username='primary', password='pass')
        p = UserProfile.objects.create(user=user, role='user')
        fa = FamilyAccount.objects.create(primary_user=p, member_name='Child One')
        self.assertIn('Child One', str(fa))

    def test_encryption_key_str(self):
        ek = EncryptionKey.objects.create(key_identifier='key-abc-123', public_key='pubdata')
        self.assertIn('key-abc-123', str(ek))

    def test_consent_log_str(self):
        cl = ConsentLog.objects.create(consent_type='data_sharing', version='1.0')
        self.assertIn('data_sharing', str(cl))

    def test_tenant_config_str(self):
        tc = TenantConfig.objects.create(tenant_name='Acme Corp')
        self.assertIn('Acme Corp', str(tc))

    def test_admin_telemetry_str(self):
        at = AdminTelemetry.objects.create(metric_name='cpu_usage', metric_value=55.5)
        self.assertIn('cpu_usage', str(at))

    def test_api_rate_limit_str(self):
        ar = APIRateLimitConfig.objects.create(endpoint='/api/v1/data')
        self.assertIn('/api/v1/data', str(ar))

    def test_anonymized_data_report_str(self):
        adr = AnonymizedDataReport.objects.create(
            report_title='Q1 Health Stats', report_type='population_health',
        )
        self.assertIn('Q1 Health Stats', str(adr))

    def test_database_scaling_config_str(self):
        dsc = DatabaseScalingConfig.objects.create(
            config_name='Primary Replica', scaling_type='read_replica',
        )
        s = str(dsc)
        self.assertIn('Primary Replica', s)
        self.assertIn('Read Replica', s)

    def test_backup_configuration_str(self):
        bc = BackupConfiguration.objects.create(
            backup_name='Nightly DB Backup', frequency='daily',
        )
        s = str(bc)
        self.assertIn('Nightly DB Backup', s)
        self.assertIn('Daily', s)

    def test_audit_log_str(self):
        al = AuditLog.objects.create(action='user_login')
        self.assertIn('user_login', str(al))


class Phase8ModelTests(TestCase):
    """Test model creation, __str__, and calculated fields for these models."""

    def test_biological_age_difference(self):
        ba = BiologicalAgeCalculation.objects.create(
            date=date(2026, 3, 1), chronological_age=40, biological_age=35,
        )
        self.assertEqual(ba.age_difference, -5.0)

    def test_biological_age_str(self):
        ba = BiologicalAgeCalculation.objects.create(
            date=date(2026, 3, 1), chronological_age=40, biological_age=35,
        )
        s = str(ba)
        self.assertIn('35', s)
        self.assertIn('40', s)

    def test_health_goal_progress(self):
        g = HealthGoal.objects.create(
            title='Test', target_value=100, current_value=75,
            start_date=date(2026, 3, 1), status='active',
        )
        self.assertEqual(g.progress_percent, 75.0)

    def test_health_goal_progress_none(self):
        g = HealthGoal.objects.create(
            title='Test', start_date=date(2026, 3, 1), status='active',
        )
        self.assertIsNone(g.progress_percent)

    def test_health_goal_str(self):
        g = HealthGoal.objects.create(
            title='Lose Weight', start_date=date(2026, 3, 1), status='active',
        )
        s = str(g)
        self.assertIn('Lose Weight', s)
        self.assertIn('active', s)

    def test_medication_schedule_str(self):
        ms = MedicationSchedule.objects.create(
            medication_name='Aspirin', dosage='100mg',
            frequency='daily', start_date=date(2026, 3, 1),
        )
        self.assertIn('Aspirin', str(ms))

    def test_critical_alert_str(self):
        ca = CriticalAlert.objects.create(
            metric_name='Heart Rate', metric_value=120,
            threshold_value=100, alert_level='warning',
        )
        self.assertIn('Heart Rate', str(ca))

    def test_health_report_str(self):
        hr = HealthReport.objects.create(
            title='Monthly Report', period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.assertIn('Monthly Report', str(hr))

    def test_predictive_biomarker_str(self):
        pb = PredictiveBiomarker.objects.create(
            biomarker_name='HbA1c', predicted_value=5.6,
            prediction_date=date(2026, 3, 1),
        )
        self.assertIn('HbA1c', str(pb))


class Phase9ModelTests(TestCase):
    """Test model creation and __str__ for these models."""

    def test_secure_viewing_link_str(self):
        from django.utils import timezone
        svl = SecureViewingLink.objects.create(
            token='abc123', expires_at=timezone.now(),
        )
        self.assertIn('expires', str(svl))

    def test_practitioner_access_str(self):
        pa = PractitionerAccess.objects.create(
            practitioner_name='Smith', practitioner_email='s@example.com',
        )
        self.assertIn('Smith', str(pa))

    def test_intake_summary_str(self):
        i = IntakeSummary.objects.create(title='New Patient')
        self.assertIn('New Patient', str(i))

    def test_data_export_str(self):
        de = DataExportRequest.objects.create(export_format='json')
        self.assertIn('json', str(de))

    def test_stakeholder_email_str(self):
        se = StakeholderEmail.objects.create(
            recipient_name='Jane Doe', recipient_email='jane@example.com',
        )
        self.assertIn('Jane Doe', str(se))


class Phase10_12ModelTests(TestCase):
    """Test model creation and __str__ for these models."""

    def test_integration_config_str(self):
        ic = IntegrationConfig.objects.create(category='genomics', feature_type='export')
        self.assertIn('Genomics', str(ic))

    def test_integration_subtask_str(self):
        ist = IntegrationSubTask.objects.create(
            phase=10, sub_task_number=1, title='Test Task',
            category='genomics', feature_type='export', status='pending',
        )
        self.assertIn('Area 10', str(ist))


class Phase5To12StatusCodeTests(TestCase):
    """Test GET requests return 200 for all list and add pages."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    # ---
    def test_wearable_device_list(self):
        self.assertEqual(self.client.get(reverse('wearable_device_list')).status_code, 200)

    def test_wearable_device_add(self):
        self.assertEqual(self.client.get(reverse('wearable_device_add')).status_code, 200)

    def test_sync_log_list(self):
        self.assertEqual(self.client.get(reverse('sync_log_list')).status_code, 200)

    # ---
    def test_sleep_list(self):
        self.assertEqual(self.client.get(reverse('sleep_list')).status_code, 200)

    def test_sleep_add(self):
        self.assertEqual(self.client.get(reverse('sleep_add')).status_code, 200)

    def test_circadian_list(self):
        self.assertEqual(self.client.get(reverse('circadian_list')).status_code, 200)

    def test_circadian_add(self):
        self.assertEqual(self.client.get(reverse('circadian_add')).status_code, 200)

    def test_dream_list(self):
        self.assertEqual(self.client.get(reverse('dream_list')).status_code, 200)

    def test_dream_add(self):
        self.assertEqual(self.client.get(reverse('dream_add')).status_code, 200)

    def test_macro_list(self):
        self.assertEqual(self.client.get(reverse('macro_list')).status_code, 200)

    def test_macro_add(self):
        self.assertEqual(self.client.get(reverse('macro_add')).status_code, 200)

    def test_micro_list(self):
        self.assertEqual(self.client.get(reverse('micro_list')).status_code, 200)

    def test_micro_add(self):
        self.assertEqual(self.client.get(reverse('micro_add')).status_code, 200)

    def test_food_list(self):
        self.assertEqual(self.client.get(reverse('food_list')).status_code, 200)

    def test_food_add(self):
        self.assertEqual(self.client.get(reverse('food_add')).status_code, 200)

    def test_fasting_list(self):
        self.assertEqual(self.client.get(reverse('fasting_list')).status_code, 200)

    def test_fasting_add(self):
        self.assertEqual(self.client.get(reverse('fasting_add')).status_code, 200)

    def test_caffeine_alcohol_list(self):
        self.assertEqual(self.client.get(reverse('caffeine_alcohol_list')).status_code, 200)

    def test_caffeine_alcohol_add(self):
        self.assertEqual(self.client.get(reverse('caffeine_alcohol_add')).status_code, 200)

    # ---
    def test_user_profile_list(self):
        self.assertEqual(self.client.get(reverse('user_profile_list')).status_code, 200)

    def test_user_profile_add(self):
        self.assertEqual(self.client.get(reverse('user_profile_add')).status_code, 200)

    def test_family_account_list(self):
        self.assertEqual(self.client.get(reverse('family_account_list')).status_code, 200)

    def test_family_account_add(self):
        self.assertEqual(self.client.get(reverse('family_account_add')).status_code, 200)

    def test_consent_log_list(self):
        self.assertEqual(self.client.get(reverse('consent_log_list')).status_code, 200)

    def test_consent_log_add(self):
        self.assertEqual(self.client.get(reverse('consent_log_add')).status_code, 200)

    def test_tenant_config_list(self):
        self.assertEqual(self.client.get(reverse('tenant_config_list')).status_code, 200)

    def test_tenant_config_add(self):
        self.assertEqual(self.client.get(reverse('tenant_config_add')).status_code, 200)

    def test_admin_telemetry_list(self):
        self.assertEqual(self.client.get(reverse('admin_telemetry_list')).status_code, 200)

    def test_admin_telemetry_add(self):
        self.assertEqual(self.client.get(reverse('admin_telemetry_add')).status_code, 200)

    def test_api_rate_limit_list(self):
        self.assertEqual(self.client.get(reverse('api_rate_limit_list')).status_code, 200)

    def test_api_rate_limit_add(self):
        self.assertEqual(self.client.get(reverse('api_rate_limit_add')).status_code, 200)

    def test_encryption_key_list(self):
        self.assertEqual(self.client.get(reverse('encryption_key_list')).status_code, 200)

    def test_encryption_key_add(self):
        self.assertEqual(self.client.get(reverse('encryption_key_add')).status_code, 200)

    def test_audit_log_list(self):
        self.assertEqual(self.client.get(reverse('audit_log_list')).status_code, 200)

    def test_audit_log_add(self):
        self.assertEqual(self.client.get(reverse('audit_log_add')).status_code, 200)

    def test_anonymized_data_list(self):
        self.assertEqual(self.client.get(reverse('anonymized_data_list')).status_code, 200)

    def test_anonymized_data_add(self):
        self.assertEqual(self.client.get(reverse('anonymized_data_add')).status_code, 200)

    def test_database_scaling_list(self):
        self.assertEqual(self.client.get(reverse('database_scaling_list')).status_code, 200)

    def test_database_scaling_add(self):
        self.assertEqual(self.client.get(reverse('database_scaling_add')).status_code, 200)

    def test_backup_config_list(self):
        self.assertEqual(self.client.get(reverse('backup_config_list')).status_code, 200)

    def test_backup_config_add(self):
        self.assertEqual(self.client.get(reverse('backup_config_add')).status_code, 200)

    # ---
    def test_medication_schedule_list(self):
        self.assertEqual(self.client.get(reverse('medication_schedule_list')).status_code, 200)

    def test_medication_schedule_add(self):
        self.assertEqual(self.client.get(reverse('medication_schedule_add')).status_code, 200)

    def test_health_goal_list(self):
        self.assertEqual(self.client.get(reverse('health_goal_list')).status_code, 200)

    def test_health_goal_add(self):
        self.assertEqual(self.client.get(reverse('health_goal_add')).status_code, 200)

    def test_critical_alert_list(self):
        self.assertEqual(self.client.get(reverse('critical_alert_list')).status_code, 200)

    def test_critical_alert_add(self):
        self.assertEqual(self.client.get(reverse('critical_alert_add')).status_code, 200)

    def test_health_report_list(self):
        self.assertEqual(self.client.get(reverse('health_report_list')).status_code, 200)

    def test_health_report_add(self):
        self.assertEqual(self.client.get(reverse('health_report_add')).status_code, 200)

    def test_biological_age_list(self):
        self.assertEqual(self.client.get(reverse('biological_age_list')).status_code, 200)

    def test_biological_age_add(self):
        self.assertEqual(self.client.get(reverse('biological_age_add')).status_code, 200)

    def test_predictive_biomarker_list(self):
        self.assertEqual(self.client.get(reverse('predictive_biomarker_list')).status_code, 200)

    def test_predictive_biomarker_add(self):
        self.assertEqual(self.client.get(reverse('predictive_biomarker_add')).status_code, 200)

    # ---
    def test_secure_viewing_link_list(self):
        self.assertEqual(self.client.get(reverse('secure_viewing_link_list')).status_code, 200)

    def test_secure_viewing_link_add(self):
        self.assertEqual(self.client.get(reverse('secure_viewing_link_add')).status_code, 200)

    def test_practitioner_access_list(self):
        self.assertEqual(self.client.get(reverse('practitioner_access_list')).status_code, 200)

    def test_practitioner_access_add(self):
        self.assertEqual(self.client.get(reverse('practitioner_access_add')).status_code, 200)

    def test_intake_summary_list(self):
        self.assertEqual(self.client.get(reverse('intake_summary_list')).status_code, 200)

    def test_intake_summary_add(self):
        self.assertEqual(self.client.get(reverse('intake_summary_add')).status_code, 200)

    def test_data_export_list(self):
        self.assertEqual(self.client.get(reverse('data_export_list')).status_code, 200)

    def test_data_export_add(self):
        self.assertEqual(self.client.get(reverse('data_export_add')).status_code, 200)

    def test_stakeholder_email_list(self):
        self.assertEqual(self.client.get(reverse('stakeholder_email_list')).status_code, 200)

    def test_stakeholder_email_add(self):
        self.assertEqual(self.client.get(reverse('stakeholder_email_add')).status_code, 200)

    # Integration Areas
    def test_integration_config_list(self):
        self.assertEqual(self.client.get(reverse('integration_config_list')).status_code, 200)

    def test_integration_config_add(self):
        self.assertEqual(self.client.get(reverse('integration_config_add')).status_code, 200)

    def test_integration_subtask_list(self):
        self.assertEqual(self.client.get(reverse('integration_subtask_list')).status_code, 200)

    def test_integration_subtask_add(self):
        self.assertEqual(self.client.get(reverse('integration_subtask_add')).status_code, 200)


class Phase5To12CRUDTests(TestCase):
    """Test POST create, edit, and delete for these models."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='crudtestuser', password='testpass123', email='crud@example.com')
        self.client.login(username='crudtestuser', password='testpass123')

    # ----- WearableDevice -----
    def test_wearable_device_add_post(self):
        response = self.client.post(reverse('wearable_device_add'), {
            'platform': 'fitbit',
            'device_name': 'Test',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(WearableDevice.objects.count(), 1)

    def test_wearable_device_edit_post(self):
        d = WearableDevice.objects.create(platform='fitbit', device_name='Test')
        response = self.client.post(reverse('wearable_device_edit', kwargs={'pk': d.pk}), {
            'platform': 'fitbit',
            'device_name': 'Updated',
        })
        self.assertEqual(response.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.device_name, 'Updated')

    def test_wearable_device_delete_post(self):
        d = WearableDevice.objects.create(platform='fitbit', device_name='Test')
        response = self.client.post(reverse('wearable_device_delete', kwargs={'pk': d.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(WearableDevice.objects.count(), 0)

    # ----- SleepLog -----
    def test_sleep_add_post(self):
        response = self.client.post(reverse('sleep_add'), {
            'date': '2026-03-01',
            'total_sleep_minutes': '420',
            'bedtime': '22:00',
            'wake_time': '06:00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SleepLog.objects.count(), 1)

    def test_sleep_edit_post(self):
        s = SleepLog.objects.create(date=date(2026, 3, 1), total_sleep_minutes=420)
        response = self.client.post(reverse('sleep_edit', kwargs={'pk': s.pk}), {
            'date': '2026-03-02',
            'total_sleep_minutes': '480',
            'bedtime': '22:00',
            'wake_time': '06:00',
        })
        self.assertEqual(response.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.total_sleep_minutes, 480)

    def test_sleep_delete_post(self):
        s = SleepLog.objects.create(date=date(2026, 3, 1), total_sleep_minutes=420)
        response = self.client.post(reverse('sleep_delete', kwargs={'pk': s.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SleepLog.objects.count(), 0)

    # ----- MacronutrientLog -----
    def test_macro_add_post(self):
        response = self.client.post(reverse('macro_add'), {
            'date': '2026-03-01',
            'protein_grams': '50',
            'carbohydrate_grams': '200',
            'fat_grams': '70',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MacronutrientLog.objects.count(), 1)

    def test_macro_edit_post(self):
        m = MacronutrientLog.objects.create(
            date=date(2026, 3, 1), protein_grams=50, carbohydrate_grams=200, fat_grams=70,
        )
        response = self.client.post(reverse('macro_edit', kwargs={'pk': m.pk}), {
            'date': '2026-03-01',
            'protein_grams': '60',
            'carbohydrate_grams': '200',
            'fat_grams': '70',
        })
        self.assertEqual(response.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.protein_grams, 60.0)

    def test_macro_delete_post(self):
        m = MacronutrientLog.objects.create(date=date(2026, 3, 1), protein_grams=50)
        response = self.client.post(reverse('macro_delete', kwargs={'pk': m.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MacronutrientLog.objects.count(), 0)

    # ----- MicronutrientLog -----
    def test_micro_add_post(self):
        response = self.client.post(reverse('micro_add'), {
            'date': '2026-03-01',
            'nutrient_name': 'Iron',
            'amount': '18',
            'unit': 'mg',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MicronutrientLog.objects.count(), 1)

    def test_micro_edit_post(self):
        m = MicronutrientLog.objects.create(
            date=date(2026, 3, 1), nutrient_name='Iron', amount=18, unit='mg',
        )
        response = self.client.post(reverse('micro_edit', kwargs={'pk': m.pk}), {
            'date': '2026-03-01',
            'nutrient_name': 'Iron',
            'amount': '25',
            'unit': 'mg',
        })
        self.assertEqual(response.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.amount, 25.0)

    def test_micro_delete_post(self):
        m = MicronutrientLog.objects.create(
            date=date(2026, 3, 1), nutrient_name='Iron', amount=18, unit='mg',
        )
        response = self.client.post(reverse('micro_delete', kwargs={'pk': m.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MicronutrientLog.objects.count(), 0)

    # ----- FoodEntry -----
    def test_food_add_post(self):
        response = self.client.post(reverse('food_add'), {
            'date': '2026-03-01',
            'food_name': 'Apple',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FoodEntry.objects.count(), 1)

    def test_food_edit_post(self):
        f = FoodEntry.objects.create(date=date(2026, 3, 1), food_name='Apple')
        response = self.client.post(reverse('food_edit', kwargs={'pk': f.pk}), {
            'date': '2026-03-01',
            'food_name': 'Banana',
        })
        self.assertEqual(response.status_code, 302)
        f.refresh_from_db()
        self.assertEqual(f.food_name, 'Banana')

    def test_food_delete_post(self):
        f = FoodEntry.objects.create(date=date(2026, 3, 1), food_name='Apple')
        response = self.client.post(reverse('food_delete', kwargs={'pk': f.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FoodEntry.objects.count(), 0)

    # ----- CircadianRhythmLog -----
    def test_circadian_add_post(self):
        response = self.client.post(reverse('circadian_add'), {
            'date': '2026-03-01',
            'wake_time': '07:00',
            'sleep_onset': '23:00',
            'light_exposure_minutes': '60',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CircadianRhythmLog.objects.count(), 1)

    def test_circadian_edit_post(self):
        c = CircadianRhythmLog.objects.create(date=date(2026, 3, 1), light_exposure_minutes=60)
        response = self.client.post(reverse('circadian_edit', kwargs={'pk': c.pk}), {
            'date': '2026-03-01',
            'light_exposure_minutes': '90',
        })
        self.assertEqual(response.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.light_exposure_minutes, 90)

    def test_circadian_delete_post(self):
        c = CircadianRhythmLog.objects.create(date=date(2026, 3, 1))
        response = self.client.post(reverse('circadian_delete', kwargs={'pk': c.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CircadianRhythmLog.objects.count(), 0)

    # ----- DreamJournal -----
    def test_dream_add_post(self):
        response = self.client.post(reverse('dream_add'), {
            'date': '2026-03-01',
            'dream_description': 'Flying over mountains',
            'lucidity_level': '3',
            'mood_on_waking': 'happy',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DreamJournal.objects.count(), 1)

    def test_dream_edit_post(self):
        d = DreamJournal.objects.create(date=date(2026, 3, 1), dream_description='Old dream')
        response = self.client.post(reverse('dream_edit', kwargs={'pk': d.pk}), {
            'date': '2026-03-01',
            'dream_description': 'Updated dream',
            'mood_on_waking': 'calm',
        })
        self.assertEqual(response.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.dream_description, 'Updated dream')

    def test_dream_delete_post(self):
        d = DreamJournal.objects.create(date=date(2026, 3, 1))
        response = self.client.post(reverse('dream_delete', kwargs={'pk': d.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DreamJournal.objects.count(), 0)

    # ----- FastingLog -----
    def test_fasting_add_post(self):
        response = self.client.post(reverse('fasting_add'), {
            'date': '2026-03-01',
            'target_hours': '16',
            'actual_hours': '16',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FastingLog.objects.count(), 1)

    def test_fasting_edit_post(self):
        f = FastingLog.objects.create(date=date(2026, 3, 1), target_hours=16, actual_hours=14)
        response = self.client.post(reverse('fasting_edit', kwargs={'pk': f.pk}), {
            'date': '2026-03-01',
            'target_hours': '16',
            'actual_hours': '16',
        })
        self.assertEqual(response.status_code, 302)
        f.refresh_from_db()
        self.assertEqual(f.actual_hours, 16.0)

    def test_fasting_delete_post(self):
        f = FastingLog.objects.create(date=date(2026, 3, 1))
        response = self.client.post(reverse('fasting_delete', kwargs={'pk': f.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FastingLog.objects.count(), 0)

    # ----- CaffeineAlcoholLog -----
    def test_caffeine_alcohol_add_post(self):
        response = self.client.post(reverse('caffeine_alcohol_add'), {
            'date': '2026-03-01',
            'substance': 'caffeine',
            'amount_mg': '200',
            'drink_name': 'Coffee',
            'time_consumed': '08:00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CaffeineAlcoholLog.objects.count(), 1)

    def test_caffeine_alcohol_edit_post(self):
        c = CaffeineAlcoholLog.objects.create(
            date=date(2026, 3, 1), substance='caffeine', amount_mg=200,
        )
        response = self.client.post(reverse('caffeine_alcohol_edit', kwargs={'pk': c.pk}), {
            'date': '2026-03-01',
            'substance': 'caffeine',
            'amount_mg': '300',
            'drink_name': 'Espresso',
        })
        self.assertEqual(response.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.amount_mg, 300.0)

    def test_caffeine_alcohol_delete_post(self):
        c = CaffeineAlcoholLog.objects.create(
            date=date(2026, 3, 1), substance='caffeine',
        )
        response = self.client.post(reverse('caffeine_alcohol_delete', kwargs={'pk': c.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CaffeineAlcoholLog.objects.count(), 0)

    # ----- UserProfile -----
    def test_user_profile_add_post(self):
        response = self.client.post(reverse('user_profile_add'), {
            'username': 'newuser',
            'role': 'user',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserProfile.objects.filter(role='user', user__username='newuser').count(), 1)

    def test_user_profile_edit_post(self):
        user = User.objects.create_user(username='testuser', password='pass')
        p = UserProfile.objects.create(user=user, role='user')
        response = self.client.post(reverse('user_profile_edit', kwargs={'pk': p.pk}), {
            'username': 'testuser',
            'role': 'admin',
        })
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.role, 'admin')

    def test_user_profile_delete_post(self):
        user = User.objects.create_user(username='testuser', password='pass')
        p = UserProfile.objects.create(user=user, role='user')
        response = self.client.post(reverse('user_profile_delete', kwargs={'pk': p.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserProfile.objects.filter(user__username='testuser').count(), 0)

    # ----- EncryptionKey -----
    def test_encryption_key_add_post(self):
        response = self.client.post(reverse('encryption_key_add'), {
            'key_identifier': 'key-test-001',
            'public_key': 'test-public-key-data',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EncryptionKey.objects.count(), 1)

    def test_encryption_key_edit_post(self):
        ek = EncryptionKey.objects.create(key_identifier='key-001', public_key='data')
        response = self.client.post(reverse('encryption_key_edit', kwargs={'pk': ek.pk}), {
            'key_identifier': 'key-002',
            'public_key': 'updated-data',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        ek.refresh_from_db()
        self.assertEqual(ek.key_identifier, 'key-002')

    def test_encryption_key_delete_post(self):
        ek = EncryptionKey.objects.create(key_identifier='key-001', public_key='data')
        response = self.client.post(reverse('encryption_key_delete', kwargs={'pk': ek.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EncryptionKey.objects.count(), 0)

    # ----- AuditLog -----
    def test_audit_log_add_post(self):
        response = self.client.post(reverse('audit_log_add'), {
            'action': 'user_login',
            'details': 'User logged in successfully',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_audit_log_edit_post(self):
        al = AuditLog.objects.create(action='user_login', details='test')
        response = self.client.post(reverse('audit_log_edit', kwargs={'pk': al.pk}), {
            'action': 'user_logout',
            'details': 'updated',
        })
        self.assertEqual(response.status_code, 302)
        al.refresh_from_db()
        self.assertEqual(al.action, 'user_logout')

    def test_audit_log_delete_post(self):
        al = AuditLog.objects.create(action='user_login')
        response = self.client.post(reverse('audit_log_delete', kwargs={'pk': al.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AuditLog.objects.count(), 0)

    # ----- AnonymizedDataReport -----
    def test_anonymized_data_add_post(self):
        response = self.client.post(reverse('anonymized_data_add'), {
            'report_title': 'Q1 Stats',
            'report_type': 'population_health',
            'total_records': '1000',
            'anonymization_method': 'k-anonymity',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AnonymizedDataReport.objects.count(), 1)

    def test_anonymized_data_edit_post(self):
        adr = AnonymizedDataReport.objects.create(
            report_title='Q1 Stats', report_type='population_health', total_records=1000,
        )
        response = self.client.post(reverse('anonymized_data_edit', kwargs={'pk': adr.pk}), {
            'report_title': 'Q2 Stats',
            'report_type': 'trend_analysis',
            'total_records': '2000',
        })
        self.assertEqual(response.status_code, 302)
        adr.refresh_from_db()
        self.assertEqual(adr.report_title, 'Q2 Stats')

    def test_anonymized_data_delete_post(self):
        adr = AnonymizedDataReport.objects.create(
            report_title='Q1 Stats', report_type='population_health',
        )
        response = self.client.post(reverse('anonymized_data_delete', kwargs={'pk': adr.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AnonymizedDataReport.objects.count(), 0)

    # ----- DatabaseScalingConfig -----
    def test_database_scaling_add_post(self):
        response = self.client.post(reverse('database_scaling_add'), {
            'config_name': 'Primary Replica',
            'scaling_type': 'read_replica',
            'max_connections': '200',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DatabaseScalingConfig.objects.count(), 1)

    def test_database_scaling_edit_post(self):
        dsc = DatabaseScalingConfig.objects.create(
            config_name='Primary Replica', scaling_type='read_replica',
        )
        response = self.client.post(reverse('database_scaling_edit', kwargs={'pk': dsc.pk}), {
            'config_name': 'Shard Config',
            'scaling_type': 'sharding',
            'max_connections': '500',
        })
        self.assertEqual(response.status_code, 302)
        dsc.refresh_from_db()
        self.assertEqual(dsc.config_name, 'Shard Config')

    def test_database_scaling_delete_post(self):
        dsc = DatabaseScalingConfig.objects.create(
            config_name='Primary Replica', scaling_type='read_replica',
        )
        response = self.client.post(reverse('database_scaling_delete', kwargs={'pk': dsc.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DatabaseScalingConfig.objects.count(), 0)

    # ----- BackupConfiguration -----
    def test_backup_config_add_post(self):
        response = self.client.post(reverse('backup_config_add'), {
            'backup_name': 'Nightly Backup',
            'frequency': 'daily',
            'retention_days': '30',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BackupConfiguration.objects.count(), 1)

    def test_backup_config_edit_post(self):
        bc = BackupConfiguration.objects.create(
            backup_name='Nightly Backup', frequency='daily',
        )
        response = self.client.post(reverse('backup_config_edit', kwargs={'pk': bc.pk}), {
            'backup_name': 'Weekly Backup',
            'frequency': 'weekly',
            'retention_days': '60',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        bc.refresh_from_db()
        self.assertEqual(bc.backup_name, 'Weekly Backup')

    def test_backup_config_delete_post(self):
        bc = BackupConfiguration.objects.create(
            backup_name='Nightly Backup', frequency='daily',
        )
        response = self.client.post(reverse('backup_config_delete', kwargs={'pk': bc.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BackupConfiguration.objects.count(), 0)

    # ----- MedicationSchedule -----
    def test_medication_schedule_add_post(self):
        response = self.client.post(reverse('medication_schedule_add'), {
            'medication_name': 'Aspirin',
            'dosage': '100mg',
            'frequency': 'daily',
            'start_date': '2026-03-01',
            'time_of_day': '08:00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MedicationSchedule.objects.count(), 1)

    def test_medication_schedule_edit_post(self):
        ms = MedicationSchedule.objects.create(
            medication_name='Aspirin', dosage='100mg',
            frequency='daily', start_date=date(2026, 3, 1),
        )
        response = self.client.post(reverse('medication_schedule_edit', kwargs={'pk': ms.pk}), {
            'medication_name': 'Aspirin',
            'dosage': '200mg',
            'frequency': 'daily',
            'start_date': '2026-03-01',
            'time_of_day': '08:00',
        })
        self.assertEqual(response.status_code, 302)
        ms.refresh_from_db()
        self.assertEqual(ms.dosage, '200mg')

    def test_medication_schedule_delete_post(self):
        ms = MedicationSchedule.objects.create(
            medication_name='Aspirin', dosage='100mg',
            frequency='daily', start_date=date(2026, 3, 1),
        )
        response = self.client.post(reverse('medication_schedule_delete', kwargs={'pk': ms.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MedicationSchedule.objects.count(), 0)

    # ----- HealthGoal -----
    def test_health_goal_add_post(self):
        response = self.client.post(reverse('health_goal_add'), {
            'title': 'Lose Weight',
            'target_value': '70',
            'unit': 'kg',
            'status': 'active',
            'start_date': '2026-03-01',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HealthGoal.objects.count(), 1)

    def test_health_goal_edit_post(self):
        g = HealthGoal.objects.create(
            title='Lose Weight', target_value=70, unit='kg',
            status='active', start_date=date(2026, 3, 1),
        )
        response = self.client.post(reverse('health_goal_edit', kwargs={'pk': g.pk}), {
            'title': 'Lose Weight',
            'target_value': '65',
            'unit': 'kg',
            'status': 'active',
            'start_date': '2026-03-01',
        })
        self.assertEqual(response.status_code, 302)
        g.refresh_from_db()
        self.assertEqual(g.target_value, 65.0)

    def test_health_goal_delete_post(self):
        g = HealthGoal.objects.create(
            title='Lose Weight', target_value=70, unit='kg',
            status='active', start_date=date(2026, 3, 1),
        )
        response = self.client.post(reverse('health_goal_delete', kwargs={'pk': g.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HealthGoal.objects.count(), 0)

    # ----- CriticalAlert -----
    def test_critical_alert_add_post(self):
        response = self.client.post(reverse('critical_alert_add'), {
            'metric_name': 'Heart Rate',
            'metric_value': '120',
            'threshold_value': '100',
            'alert_level': 'warning',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CriticalAlert.objects.count(), 1)

    def test_critical_alert_edit_post(self):
        ca = CriticalAlert.objects.create(
            metric_name='Heart Rate', metric_value=120,
            threshold_value=100, alert_level='warning',
        )
        response = self.client.post(reverse('critical_alert_edit', kwargs={'pk': ca.pk}), {
            'metric_name': 'Heart Rate',
            'metric_value': '130',
            'threshold_value': '100',
            'alert_level': 'critical',
        })
        self.assertEqual(response.status_code, 302)
        ca.refresh_from_db()
        self.assertEqual(ca.metric_value, 130.0)

    def test_critical_alert_delete_post(self):
        ca = CriticalAlert.objects.create(
            metric_name='Heart Rate', metric_value=120,
            threshold_value=100, alert_level='warning',
        )
        response = self.client.post(reverse('critical_alert_delete', kwargs={'pk': ca.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CriticalAlert.objects.count(), 0)

    # ----- IntegrationConfig -----
    def test_integration_config_add_post(self):
        response = self.client.post(reverse('integration_config_add'), {
            'category': 'genomics',
            'feature_type': 'export',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntegrationConfig.objects.count(), 1)

    def test_integration_config_edit_post(self):
        ic = IntegrationConfig.objects.create(category='genomics', feature_type='export')
        response = self.client.post(reverse('integration_config_edit', kwargs={'pk': ic.pk}), {
            'category': 'genomics',
            'feature_type': 'reporting',
        })
        self.assertEqual(response.status_code, 302)
        ic.refresh_from_db()
        self.assertEqual(ic.feature_type, 'reporting')

    def test_integration_config_delete_post(self):
        ic = IntegrationConfig.objects.create(category='genomics', feature_type='export')
        response = self.client.post(reverse('integration_config_delete', kwargs={'pk': ic.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntegrationConfig.objects.count(), 0)

    # ----- IntegrationSubTask -----
    def test_integration_subtask_add_post(self):
        count_before = IntegrationSubTask.objects.count()
        response = self.client.post(reverse('integration_subtask_add'), {
            'phase': '10',
            'sub_task_number': '1',
            'title': 'Test',
            'category': 'genomics',
            'feature_type': 'export',
            'status': 'pending',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntegrationSubTask.objects.count(), count_before + 1)

    def test_integration_subtask_edit_post(self):
        ist = IntegrationSubTask.objects.create(
            phase=10, sub_task_number=1, title='Test',
            category='genomics', feature_type='export', status='pending',
        )
        response = self.client.post(reverse('integration_subtask_edit', kwargs={'pk': ist.pk}), {
            'phase': '10',
            'sub_task_number': '1',
            'title': 'Updated',
            'category': 'genomics',
            'feature_type': 'export',
            'status': 'in_progress',
        })
        self.assertEqual(response.status_code, 302)
        ist.refresh_from_db()
        self.assertEqual(ist.title, 'Updated')

    def test_integration_subtask_delete_post(self):
        ist = IntegrationSubTask.objects.create(
            phase=10, sub_task_number=1, title='Test',
            category='genomics', feature_type='export', status='pending',
        )
        count_before = IntegrationSubTask.objects.count()
        response = self.client.post(reverse('integration_subtask_delete', kwargs={'pk': ist.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntegrationSubTask.objects.count(), count_before - 1)


class Phase11DashboardTests(TestCase):
    """Test Interoperability dashboard view."""

    def setUp(self):
        self.client = Client()
        IntegrationSubTask.objects.filter(phase=11).delete()
        IntegrationSubTask.objects.create(
            phase=11, sub_task_number=91, title='Macronutrients User Dashboard',
            category='macronutrients', feature_type='user_dashboard', status='pending',
        )
        IntegrationSubTask.objects.create(
            phase=11, sub_task_number=92, title='DICOM Predictive Modeling',
            category='dicom', feature_type='predictive_modeling', status='in_progress',
        )
        IntegrationSubTask.objects.create(
            phase=11, sub_task_number=99, title='IHE_XDM Predictive Modeling',
            category='ihe_xdm', feature_type='predictive_modeling', status='completed',
        )
        IntegrationSubTask.objects.create(
            phase=11, sub_task_number=124, title='FHIR R4 Predictive Modeling',
            category='fhir_r4', feature_type='predictive_modeling', status='pending',
        )
        IntegrationSubTask.objects.create(
            phase=11, sub_task_number=144, title='HL7 v3 Reporting Tools',
            category='hl7_v3', feature_type='reporting', status='pending',
        )

    def test_dashboard_status_code(self):
        response = self.client.get(reverse('phase11_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_subtasks(self):
        response = self.client.get(reverse('phase11_dashboard'))
        self.assertContains(response, 'Macronutrients User Dashboard')
        self.assertContains(response, 'DICOM Predictive Modeling')
        self.assertContains(response, 'IHE_XDM Predictive Modeling')

    def test_dashboard_summary_counts(self):
        response = self.client.get(reverse('phase11_dashboard'))
        self.assertEqual(response.context['total'], 5)
        self.assertEqual(response.context['completed'], 1)
        self.assertEqual(response.context['in_progress'], 1)
        self.assertEqual(response.context['pending'], 3)

    def test_dashboard_filter_by_category(self):
        response = self.client.get(reverse('phase11_dashboard'), {'category': 'ihe_xdm'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['subtasks']), 1)
        self.assertContains(response, 'IHE_XDM Predictive Modeling')

    def test_dashboard_filter_by_feature_type(self):
        response = self.client.get(reverse('phase11_dashboard'), {'feature_type': 'predictive_modeling'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['subtasks']), 3)

    def test_dashboard_filter_by_status(self):
        response = self.client.get(reverse('phase11_dashboard'), {'status': 'pending'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['subtasks']), 3)

    def test_dashboard_category_summary(self):
        response = self.client.get(reverse('phase11_dashboard'))
        summary = response.context['category_summary']
        self.assertIn('IHE_XDM', summary)
        self.assertEqual(summary['IHE_XDM']['total'], 1)
        self.assertEqual(summary['IHE_XDM']['completed'], 1)

    def test_dashboard_excludes_other_phases(self):
        IntegrationSubTask.objects.create(
            phase=10, sub_task_number=1, title='Genomics Task',
            category='genomics', feature_type='export', status='pending',
        )
        response = self.client.get(reverse('phase11_dashboard'))
        self.assertNotContains(response, 'Genomics Task')
        self.assertEqual(response.context['total'], 5)

    def test_dashboard_interoperability_categories(self):
        response = self.client.get(reverse('phase11_dashboard'))
        self.assertContains(response, 'Interoperability')
        self.assertContains(response, 'IHE_XDM')
        self.assertContains(response, 'FHIR R4')
        self.assertContains(response, 'HL7 v3')


class Phase11SubTaskModelTests(TestCase):
    """Test IntegrationSubTask model with interoperability-specific data."""

    def setUp(self):
        IntegrationSubTask.objects.filter(phase=11).delete()

    def test_phase11_subtask_creation(self):
        ist = IntegrationSubTask.objects.create(
            phase=11, sub_task_number=104, title='IHE_XDM Data Pipeline',
            category='ihe_xdm', feature_type='data_pipeline', status='pending',
        )
        self.assertEqual(str(ist), 'Area 11 Sub-task 104: IHE_XDM Data Pipeline')
        self.assertEqual(ist.phase, 11)
        self.assertEqual(ist.category, 'ihe_xdm')
        self.assertEqual(ist.feature_type, 'data_pipeline')

    def test_phase11_subtask_unique_constraint(self):
        IntegrationSubTask.objects.create(
            phase=11, sub_task_number=91, title='Task A',
            category='macronutrients', feature_type='user_dashboard', status='pending',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            IntegrationSubTask.objects.create(
                phase=11, sub_task_number=91, title='Task B',
                category='dicom', feature_type='export', status='pending',
            )

    def test_phase11_subtask_status_transitions(self):
        ist = IntegrationSubTask.objects.create(
            phase=11, sub_task_number=156, title='IHE_XDM Api Syncing',
            category='ihe_xdm', feature_type='api_syncing', status='pending',
        )
        ist.status = 'in_progress'
        ist.save()
        ist.refresh_from_db()
        self.assertEqual(ist.status, 'in_progress')

        ist.status = 'completed'
        ist.save()
        ist.refresh_from_db()
        self.assertEqual(ist.status, 'completed')
        self.assertEqual(IntegrationSubTask.objects.count(), 1)


class Phase9SecureViewingLinkTests(TestCase):
    """Test secure viewing link token generation, expiration, and public share view."""

    def setUp(self):
        self.client = Client()

    def test_auto_token_generation(self):
        """Tokens should be auto-generated when creating a link."""
        from django.utils import timezone
        from datetime import timedelta
        expires = (timezone.now() + timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('secure_viewing_link_add'), {
            'data_types': 'blood_tests,vitals',
            'expires_at': expires,
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SecureViewingLink.objects.count(), 1)
        link = SecureViewingLink.objects.first()
        self.assertTrue(len(link.token) > 20)
        self.assertTrue(link.is_active)

    def test_token_uniqueness(self):
        """Each generated token should be unique."""
        token1 = SecureViewingLink.generate_token()
        token2 = SecureViewingLink.generate_token()
        self.assertNotEqual(token1, token2)

    def test_is_valid_property(self):
        """is_valid should return True for active, non-expired links."""
        from django.utils import timezone
        from datetime import timedelta
        valid_link = SecureViewingLink.objects.create(
            token='valid-token', expires_at=timezone.now() + timedelta(hours=24),
            is_active=True,
        )
        self.assertTrue(valid_link.is_valid)

    def test_is_expired_property(self):
        """is_expired should return True for expired links."""
        from django.utils import timezone
        from datetime import timedelta
        expired_link = SecureViewingLink.objects.create(
            token='expired-token', expires_at=timezone.now() - timedelta(hours=1),
            is_active=True,
        )
        self.assertTrue(expired_link.is_expired)
        self.assertFalse(expired_link.is_valid)

    def test_inactive_link_not_valid(self):
        """Inactive links should not be valid."""
        from django.utils import timezone
        from datetime import timedelta
        inactive_link = SecureViewingLink.objects.create(
            token='inactive-token', expires_at=timezone.now() + timedelta(hours=24),
            is_active=False,
        )
        self.assertFalse(inactive_link.is_valid)

    def test_shared_view_valid_link(self):
        """Public share view should work for valid links."""
        from django.utils import timezone
        from datetime import timedelta
        link = SecureViewingLink.objects.create(
            token='share-test-token', expires_at=timezone.now() + timedelta(hours=24),
            is_active=True,
        )
        response = self.client.get(reverse('secure_link_shared_view', kwargs={'token': 'share-test-token'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shared Health Data')
        link.refresh_from_db()
        self.assertEqual(link.access_count, 1)

    def test_shared_view_increments_access_count(self):
        """Each view should increment access count."""
        from django.utils import timezone
        from datetime import timedelta
        link = SecureViewingLink.objects.create(
            token='count-token', expires_at=timezone.now() + timedelta(hours=24),
            is_active=True,
        )
        self.client.get(reverse('secure_link_shared_view', kwargs={'token': 'count-token'}))
        self.client.get(reverse('secure_link_shared_view', kwargs={'token': 'count-token'}))
        link.refresh_from_db()
        self.assertEqual(link.access_count, 2)

    def test_shared_view_expired_link(self):
        """Expired link should show expired page."""
        from django.utils import timezone
        from datetime import timedelta
        SecureViewingLink.objects.create(
            token='expired-share-token', expires_at=timezone.now() - timedelta(hours=1),
            is_active=True,
        )
        response = self.client.get(reverse('secure_link_shared_view', kwargs={'token': 'expired-share-token'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Expired')

    def test_shared_view_inactive_link(self):
        """Inactive link should show expired page."""
        from django.utils import timezone
        from datetime import timedelta
        SecureViewingLink.objects.create(
            token='inactive-share-token', expires_at=timezone.now() + timedelta(hours=24),
            is_active=False,
        )
        response = self.client.get(reverse('secure_link_shared_view', kwargs={'token': 'inactive-share-token'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'deactivated')

    def test_shared_view_with_data(self):
        """Shared view should display health data when available."""
        from django.utils import timezone
        from datetime import timedelta
        BloodTest.objects.create(test_name='Glucose', value=95, unit='mg/dL', date=date(2026, 3, 1))
        link = SecureViewingLink.objects.create(
            token='data-token', expires_at=timezone.now() + timedelta(hours=24),
            is_active=True, data_types='blood_tests',
        )
        response = self.client.get(reverse('secure_link_shared_view', kwargs={'token': 'data-token'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Glucose')

    def test_shared_view_invalid_token_404(self):
        """Non-existent tokens should return 404."""
        response = self.client.get(reverse('secure_link_shared_view', kwargs={'token': 'nonexistent'}))
        self.assertEqual(response.status_code, 404)

    def test_edit_link(self):
        """Editing should not change the token."""
        from django.utils import timezone
        from datetime import timedelta
        link = SecureViewingLink.objects.create(
            token='edit-test-token', expires_at=timezone.now() + timedelta(hours=24),
            is_active=True,
        )
        new_expires = (timezone.now() + timedelta(hours=48)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(reverse('secure_viewing_link_edit', kwargs={'pk': link.pk}), {
            'data_types': 'vitals',
            'expires_at': new_expires,
            'is_active': 'on',
        })
        link.refresh_from_db()
        self.assertEqual(link.token, 'edit-test-token')
        self.assertEqual(link.data_types, 'vitals')


class Phase9PractitionerPortalTests(TestCase):
    """Test practitioner portal and access request workflow."""

    def setUp(self):
        self.client = Client()

    def test_portal_page_loads(self):
        response = self.client.get(reverse('practitioner_portal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Practitioner Portal')

    def test_request_access_page_loads(self):
        response = self.client.get(reverse('practitioner_request_access'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Request Patient Data Access')

    def test_submit_access_request(self):
        response = self.client.post(reverse('practitioner_request_access'), {
            'practitioner_name': 'Dr. Smith',
            'practitioner_email': 'smith@hospital.com',
            'specialty': 'Cardiology',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PractitionerAccess.objects.count(), 1)
        pa = PractitionerAccess.objects.first()
        self.assertEqual(pa.access_status, 'pending')
        self.assertEqual(pa.practitioner_name, 'Dr. Smith')

    def test_portal_with_approved_access(self):
        """Portal should show patient data for approved practitioners."""
        from django.utils import timezone
        PractitionerAccess.objects.create(
            practitioner_name='Dr. Jones',
            practitioner_email='jones@hospital.com',
            access_status='approved',
            granted_at=timezone.now(),
        )
        response = self.client.post(reverse('practitioner_portal'), {
            'practitioner_email': 'jones@hospital.com',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Approved Access Records')

    def test_portal_with_no_access(self):
        """Portal should show error for unapproved emails."""
        response = self.client.post(reverse('practitioner_portal'), {
            'practitioner_email': 'unknown@hospital.com',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No approved access found')

    def test_portal_with_pending_access(self):
        """Pending access should not grant portal data."""
        PractitionerAccess.objects.create(
            practitioner_name='Dr. Pending',
            practitioner_email='pending@hospital.com',
            access_status='pending',
        )
        response = self.client.post(reverse('practitioner_portal'), {
            'practitioner_email': 'pending@hospital.com',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No approved access found')

    def test_approve_practitioner_sets_granted_at(self):
        """Approving a practitioner should set granted_at timestamp and link the patient."""
        user = User.objects.create_user(username='patient_user', password='testpass123')
        self.client.login(username='patient_user', password='testpass123')
        pa = PractitionerAccess.objects.create(
            practitioner_name='Dr. New',
            practitioner_email='new@hospital.com',
            access_status='pending',
        )
        self.assertIsNone(pa.granted_at)
        self.client.post(reverse('practitioner_access_edit', kwargs={'pk': pa.pk}), {
            'practitioner_name': 'Dr. New',
            'practitioner_email': 'new@hospital.com',
            'specialty': 'General',
            'access_status': 'approved',
        })
        pa.refresh_from_db()
        self.assertEqual(pa.access_status, 'approved')
        self.assertIsNotNone(pa.granted_at)
        self.assertEqual(pa.patient, user)

    def test_portal_only_shows_authorized_patient_data(self):
        """Portal must not expose data belonging to patients who did not authorize the practitioner."""
        from django.utils import timezone
        patient_a = User.objects.create_user(username='patient_a', password='testpass123')
        patient_b = User.objects.create_user(username='patient_b', password='testpass123')
        # Only patient_a authorized Dr. Smith
        PractitionerAccess.objects.create(
            practitioner_name='Dr. Smith',
            practitioner_email='smith@hospital.com',
            access_status='approved',
            granted_at=timezone.now(),
            patient=patient_a,
        )
        # Create health data for both patients
        BloodTest.objects.create(
            user=patient_a, test_name='Glucose', value=90.0, unit='mg/dL',
            date=timezone.now().date(),
        )
        BloodTest.objects.create(
            user=patient_b, test_name='Cholesterol', value=180.0, unit='mg/dL',
            date=timezone.now().date(),
        )
        response = self.client.post(reverse('practitioner_portal'), {
            'practitioner_email': 'smith@hospital.com',
        })
        self.assertEqual(response.status_code, 200)
        patient_data = response.context.get('patient_data', {})
        blood_test_names = [bt['test_name'] for bt in patient_data.get('blood_tests', [])]
        # Dr. Smith should only see patient_a's Glucose, not patient_b's Cholesterol
        self.assertIn('Glucose', blood_test_names)
        self.assertNotIn('Cholesterol', blood_test_names)

    def test_request_access_requires_name_and_email(self):
        """Access request without name/email should not create entry."""
        response = self.client.post(reverse('practitioner_request_access'), {
            'practitioner_name': '',
            'practitioner_email': '',
        })
        self.assertEqual(PractitionerAccess.objects.count(), 0)


class Phase9IntakeSummaryGenerateTests(TestCase):
    """Test automated intake summary generation."""

    def setUp(self):
        self.client = Client()

    def test_generate_empty_data(self):
        """Generate should work even with no health data."""
        response = self.client.get(reverse('intake_summary_generate'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntakeSummary.objects.count(), 1)
        summary = IntakeSummary.objects.first()
        self.assertIn('Intake Summary', summary.title)
        self.assertIn('No health data available', summary.summary_text)

    def test_generate_with_blood_tests(self):
        """Generate should include blood test data."""
        BloodTest.objects.create(
            test_name='Glucose', value=95, unit='mg/dL', date=date(2026, 3, 1),
            normal_min=70, normal_max=100,
        )
        BloodTest.objects.create(
            test_name='Cholesterol', value=250, unit='mg/dL', date=date(2026, 3, 1),
            normal_min=100, normal_max=200,
        )
        response = self.client.get(reverse('intake_summary_generate'))
        self.assertEqual(response.status_code, 302)
        summary = IntakeSummary.objects.first()
        self.assertIn('Glucose', summary.summary_text)
        self.assertIn('Cholesterol', summary.conditions)

    def test_generate_with_vitals(self):
        """Generate should include vital signs."""
        VitalSign.objects.create(
            date=date(2026, 3, 1), systolic_bp=120, diastolic_bp=80,
            heart_rate=72, bbt=36.6,
        )
        response = self.client.get(reverse('intake_summary_generate'))
        self.assertEqual(response.status_code, 302)
        summary = IntakeSummary.objects.first()
        self.assertIn('BP: 120/80', summary.summary_text)
        self.assertIn('HR: 72', summary.summary_text)

    def test_generate_with_medications(self):
        """Generate should include medications."""
        MedicationSchedule.objects.create(
            medication_name='Aspirin', dosage='100mg',
            frequency='daily', start_date=date(2026, 3, 1),
        )
        response = self.client.get(reverse('intake_summary_generate'))
        self.assertEqual(response.status_code, 302)
        summary = IntakeSummary.objects.first()
        self.assertIn('Aspirin', summary.medications)

    def test_generate_out_of_range(self):
        """Generate should flag out-of-range results."""
        BloodTest.objects.create(
            test_name='TSH', value=8.5, unit='mIU/L', date=date(2026, 3, 1),
            normal_min=0.5, normal_max=4.5,
        )
        self.client.get(reverse('intake_summary_generate'))
        summary = IntakeSummary.objects.first()
        self.assertIn('Out-of-range', summary.conditions)
        self.assertIn('TSH', summary.conditions)


class Phase9DataExportTests(TestCase):
    """Test comprehensive data export in JSON and XML formats."""

    def setUp(self):
        self.client = Client()
        BloodTest.objects.create(
            test_name='Glucose', value=95, unit='mg/dL', date=date(2026, 3, 1),
        )
        VitalSign.objects.create(
            date=date(2026, 3, 1), systolic_bp=120, diastolic_bp=80, heart_rate=72,
        )

    def test_create_export_request(self):
        response = self.client.post(reverse('data_export_add'), {
            'export_format': 'json',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DataExportRequest.objects.count(), 1)
        export = DataExportRequest.objects.first()
        self.assertEqual(export.status, 'completed')
        self.assertIsNotNone(export.completed_at)

    def test_json_download(self):
        """JSON export should return valid JSON with health data."""
        export = DataExportRequest.objects.create(
            export_format='json', status='completed',
        )
        response = self.client.get(reverse('data_export_download', kwargs={'pk': export.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response['Content-Disposition'])
        data = json.loads(response.content)
        self.assertIn('blood_tests', data)
        self.assertIn('vitals', data)
        self.assertEqual(len(data['blood_tests']), 1)
        self.assertEqual(data['blood_tests'][0]['test_name'], 'Glucose')

    def test_xml_download(self):
        """XML export should return valid XML with health data."""
        export = DataExportRequest.objects.create(
            export_format='xml', status='completed',
        )
        response = self.client.get(reverse('data_export_download', kwargs={'pk': export.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        self.assertIn('attachment', response['Content-Disposition'])
        content = response.content.decode()
        self.assertIn('<?xml', content)
        self.assertIn('<health_data', content)
        self.assertIn('<blood_tests>', content)
        self.assertIn('Glucose', content)

    def test_download_nonexistent_export(self):
        """Downloading non-existent export should return 404."""
        response = self.client.get(reverse('data_export_download', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)

    def test_json_export_contains_all_sections(self):
        """JSON export should contain all data sections."""
        export = DataExportRequest.objects.create(
            export_format='json', status='completed',
        )
        response = self.client.get(reverse('data_export_download', kwargs={'pk': export.pk}))
        data = json.loads(response.content)
        for section in ['blood_tests', 'vitals', 'medications', 'body_composition', 'sleep_logs']:
            self.assertIn(section, data)

    def test_xml_export_filename(self):
        """XML export filename should include the export ID."""
        export = DataExportRequest.objects.create(
            export_format='xml', status='completed',
        )
        response = self.client.get(reverse('data_export_download', kwargs={'pk': export.pk}))
        self.assertIn(f'health_export_{export.pk}.xml', response['Content-Disposition'])


class Phase9StakeholderEmailTests(TestCase):
    """Test stakeholder email sending functionality."""

    def setUp(self):
        self.client = Client()

    def test_send_email_to_active_stakeholder(self):
        """Sending to active stakeholder should succeed."""
        from django.core import mail
        se = StakeholderEmail.objects.create(
            recipient_name='Jane Doe',
            recipient_email='jane@example.com',
            frequency='monthly',
            is_active=True,
        )
        response = self.client.get(reverse('stakeholder_email_send', kwargs={'pk': se.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Health Summary', mail.outbox[0].subject)
        self.assertIn('jane@example.com', mail.outbox[0].to)
        se.refresh_from_db()
        self.assertIsNotNone(se.last_sent)

    def test_send_email_to_inactive_stakeholder(self):
        """Sending to inactive stakeholder should fail gracefully."""
        from django.core import mail
        se = StakeholderEmail.objects.create(
            recipient_name='John Doe',
            recipient_email='john@example.com',
            frequency='monthly',
            is_active=False,
        )
        response = self.client.get(reverse('stakeholder_email_send', kwargs={'pk': se.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_email_contains_health_data(self):
        """Email should contain health summary data."""
        from django.core import mail
        VitalSign.objects.create(
            date=date(2026, 3, 1), systolic_bp=120, diastolic_bp=80, heart_rate=72,
        )
        BloodTest.objects.create(
            test_name='Glucose', value=95, unit='mg/dL', date=date(2026, 3, 1),
        )
        se = StakeholderEmail.objects.create(
            recipient_name='Care Team',
            recipient_email='careteam@example.com',
            frequency='monthly',
            is_active=True,
        )
        self.client.get(reverse('stakeholder_email_send', kwargs={'pk': se.pk}))
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('Blood Pressure: 120/80', body)
        self.assertIn('Glucose', body)
        self.assertIn('Health Summary Report', body)

    def test_send_email_flags_out_of_range(self):
        """Email should flag out-of-range values."""
        from django.core import mail
        BloodTest.objects.create(
            test_name='Cholesterol', value=280, unit='mg/dL', date=date(2026, 3, 1),
            normal_min=100, normal_max=200,
        )
        se = StakeholderEmail.objects.create(
            recipient_name='Family',
            recipient_email='family@example.com',
            frequency='monthly',
            is_active=True,
        )
        self.client.get(reverse('stakeholder_email_send', kwargs={'pk': se.pk}))
        body = mail.outbox[0].body
        self.assertIn('OUT OF RANGE', body)

    def test_send_nonexistent_stakeholder(self):
        """Sending to nonexistent stakeholder should return 404."""
        response = self.client.get(reverse('stakeholder_email_send', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)


# ===== Tests for Enhanced Model Logic =====

class SleepLogAutoScoreTests(TestCase):
    def test_auto_calculate_quality_score_on_save(self):
        """SleepLog should auto-calculate quality score when not explicitly provided."""
        log = SleepLog.objects.create(
            date=date.today(),
            total_sleep_minutes=480,
            deep_sleep_minutes=96,
            rem_minutes=120,
            light_sleep_minutes=264,
            awake_minutes=20,
        )
        self.assertIsNotNone(log.sleep_quality_score)
        self.assertGreater(log.sleep_quality_score, 0)

    def test_explicit_quality_score_preserved(self):
        """When quality score is explicitly set, it should not be overwritten."""
        log = SleepLog.objects.create(
            date=date.today(),
            total_sleep_minutes=480,
            deep_sleep_minutes=96,
            sleep_quality_score=42.0,
        )
        self.assertEqual(log.sleep_quality_score, 42.0)

    def test_no_data_no_score(self):
        """Without sleep minutes, no quality score should be set."""
        log = SleepLog.objects.create(date=date.today())
        self.assertIsNone(log.sleep_quality_score)


class MacronutrientLogAutoCalcTests(TestCase):
    def test_auto_calculate_calories(self):
        """Calories should be auto-calculated from macros when not provided."""
        log = MacronutrientLog.objects.create(
            date=date.today(),
            protein_grams=100,
            carbohydrate_grams=200,
            fat_grams=50,
        )
        # 100*4 + 200*4 + 50*9 = 400 + 800 + 450 = 1650
        self.assertEqual(log.calories, 1650.0)

    def test_explicit_calories_preserved(self):
        """When calories are explicitly set, they should not be overwritten."""
        log = MacronutrientLog.objects.create(
            date=date.today(),
            protein_grams=100,
            calories=2000,
        )
        self.assertEqual(log.calories, 2000)

    def test_macro_ratios(self):
        """Macro ratios should return protein/carb/fat percentages."""
        log = MacronutrientLog(
            date=date.today(),
            protein_grams=100,
            carbohydrate_grams=200,
            fat_grams=50,
        )
        ratios = log.macro_ratios
        self.assertIsNotNone(ratios)
        self.assertAlmostEqual(ratios['protein_pct'] + ratios['carb_pct'] + ratios['fat_pct'], 100.0, places=0)


class FastingLogAutoCalcTests(TestCase):
    def test_auto_calculate_actual_hours(self):
        """actual_hours should be auto-calculated from fast_start and fast_end."""
        start = timezone.now()
        end = start + timedelta(hours=16)
        log = FastingLog.objects.create(
            date=date.today(),
            fast_start=start,
            fast_end=end,
            target_hours=16,
        )
        self.assertIsNotNone(log.actual_hours)
        self.assertAlmostEqual(log.actual_hours, 16.0, places=1)

    def test_explicit_actual_hours_preserved(self):
        """When actual_hours is explicitly set, it should not be overwritten."""
        start = timezone.now()
        end = start + timedelta(hours=16)
        log = FastingLog.objects.create(
            date=date.today(),
            fast_start=start,
            fast_end=end,
            actual_hours=14.0,
        )
        self.assertEqual(log.actual_hours, 14.0)

    def test_goal_progress_percent(self):
        """goal_progress_percent should calculate percentage of goal achieved."""
        log = FastingLog(date=date.today(), actual_hours=12, target_hours=16)
        self.assertEqual(log.goal_progress_percent, 75.0)


class MetabolicLogHomaIRTests(TestCase):
    def test_homa_ir_calculation(self):
        """HOMA-IR should be calculated from blood glucose and insulin."""
        log = MetabolicLog(date=date.today(), blood_glucose=90, insulin_level=10)
        # (90 * 10) / 405 = 2.22
        self.assertAlmostEqual(log.homa_ir, 2.22, places=2)

    def test_homa_ir_category_normal(self):
        log = MetabolicLog(date=date.today(), blood_glucose=80, insulin_level=4)
        # (80 * 4) / 405 = 0.79
        self.assertEqual(log.homa_ir_category, 'normal')

    def test_homa_ir_category_borderline(self):
        log = MetabolicLog(date=date.today(), blood_glucose=100, insulin_level=8)
        # (100 * 8) / 405 = 1.98
        self.assertEqual(log.homa_ir_category, 'borderline')

    def test_homa_ir_category_insulin_resistant(self):
        log = MetabolicLog(date=date.today(), blood_glucose=130, insulin_level=15)
        # (130 * 15) / 405 = 4.81
        self.assertEqual(log.homa_ir_category, 'insulin_resistant')

    def test_homa_ir_none_when_missing_data(self):
        log = MetabolicLog(date=date.today(), blood_glucose=90)
        self.assertIsNone(log.homa_ir)
        self.assertIsNone(log.homa_ir_category)


class HealthGoalAutoCompleteTests(TestCase):
    def test_auto_complete_on_save(self):
        """Goal should auto-complete when current_value >= target_value."""
        goal = HealthGoal.objects.create(
            title='Lose weight',
            target_value=10,
            current_value=10,
            start_date=date.today(),
        )
        self.assertEqual(goal.status, 'completed')

    def test_stays_active_when_not_met(self):
        """Goal should stay active when target not reached."""
        goal = HealthGoal.objects.create(
            title='Lose weight',
            target_value=10,
            current_value=5,
            start_date=date.today(),
        )
        self.assertEqual(goal.status, 'active')

    def test_paused_not_auto_completed(self):
        """Paused goals should not be auto-completed."""
        goal = HealthGoal.objects.create(
            title='Lose weight',
            target_value=10,
            current_value=15,
            status='paused',
            start_date=date.today(),
        )
        self.assertEqual(goal.status, 'paused')

    def test_is_past_due(self):
        """is_past_due should return True when target date has passed."""
        goal = HealthGoal(
            title='Test',
            status='active',
            target_date=date.today() - timedelta(days=1),
            start_date=date.today() - timedelta(days=30),
        )
        self.assertTrue(goal.is_past_due)


class MedicationScheduleOverdueTests(TestCase):
    def test_is_overdue_when_past_end_date(self):
        """Should be overdue when end_date has passed and still active."""
        med = MedicationSchedule(
            medication_name='Aspirin',
            dosage='100mg',
            frequency='daily',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=1),
            is_active=True,
        )
        self.assertTrue(med.is_overdue)

    def test_not_overdue_when_inactive(self):
        """Should not be overdue when inactive."""
        med = MedicationSchedule(
            medication_name='Aspirin',
            dosage='100mg',
            frequency='daily',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=1),
            is_active=False,
        )
        self.assertFalse(med.is_overdue)

    def test_days_remaining(self):
        """days_remaining should return correct number of days."""
        med = MedicationSchedule(
            medication_name='Aspirin',
            dosage='100mg',
            frequency='daily',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            is_active=True,
        )
        self.assertEqual(med.days_remaining, 5)


class CriticalAlertAutoCheckTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_auto_check_creates_alerts_for_out_of_range_blood_test(self):
        """Auto-check should create alerts for blood tests outside normal range."""
        BloodTest.objects.create(
            test_name='Glucose', value=250, unit='mg/dL',
            date=date.today(), normal_min=70, normal_max=100,
        )
        new_alerts = CriticalAlert.check_and_create_alerts()
        self.assertGreater(len(new_alerts), 0)
        self.assertEqual(new_alerts[0].metric_name, 'Glucose')

    def test_auto_check_creates_alerts_for_high_bp(self):
        """Auto-check should create alerts for elevated blood pressure."""
        VitalSign.objects.create(
            date=date.today(), systolic_bp=190, diastolic_bp=95,
        )
        new_alerts = CriticalAlert.check_and_create_alerts()
        bp_alerts = [a for a in new_alerts if 'Blood Pressure' in a.metric_name]
        self.assertGreater(len(bp_alerts), 0)

    def test_auto_check_no_alerts_when_normal(self):
        """Auto-check should not create alerts when all values are normal."""
        BloodTest.objects.create(
            test_name='Glucose', value=90, unit='mg/dL',
            date=date.today(), normal_min=70, normal_max=100,
        )
        VitalSign.objects.create(
            date=date.today(), systolic_bp=120, diastolic_bp=80, heart_rate=72,
        )
        new_alerts = CriticalAlert.check_and_create_alerts()
        self.assertEqual(len(new_alerts), 0)

    def test_auto_check_endpoint(self):
        """Auto-check endpoint should redirect to alert list."""
        response = self.client.post(reverse('critical_alert_auto_check'))
        self.assertEqual(response.status_code, 302)

    def test_auto_check_alerts_for_low_spo2(self):
        """Auto-check should create alerts for low SpO2."""
        VitalSign.objects.create(date=date.today(), spo2=88)
        new_alerts = CriticalAlert.check_and_create_alerts()
        spo2_alerts = [a for a in new_alerts if 'SpO2' in a.metric_name]
        self.assertGreater(len(spo2_alerts), 0)
        self.assertEqual(spo2_alerts[0].alert_level, 'emergency')

    def test_auto_check_alerts_for_high_homa_ir(self):
        """Auto-check should create alerts for elevated HOMA-IR."""
        MetabolicLog.objects.create(
            date=date.today(), blood_glucose=150, insulin_level=20,
        )
        new_alerts = CriticalAlert.check_and_create_alerts()
        homa_alerts = [a for a in new_alerts if 'HOMA-IR' in a.metric_name]
        self.assertGreater(len(homa_alerts), 0)


class WearableSyncTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_trigger_sync_creates_log(self):
        """trigger_sync should create a sync log entry."""
        device = WearableDevice.objects.create(
            platform='fitbit', device_name='Charge 5', is_active=True,
        )
        sync_log = device.trigger_sync()
        self.assertEqual(sync_log.status, 'success')
        self.assertGreater(sync_log.records_synced, 0)
        device.refresh_from_db()
        self.assertIsNotNone(device.last_synced)

    def test_trigger_sync_inactive_device(self):
        """Syncing an inactive device should fail."""
        device = WearableDevice.objects.create(
            platform='fitbit', device_name='Charge 5', is_active=False,
        )
        sync_log = device.trigger_sync()
        self.assertEqual(sync_log.status, 'failed')
        self.assertIn('not active', sync_log.error_message)

    def test_sync_endpoint(self):
        """Sync endpoint should redirect to device list."""
        device = WearableDevice.objects.create(
            platform='fitbit', device_name='Charge 5', is_active=True,
        )
        response = self.client.post(reverse('wearable_sync', kwargs={'pk': device.pk}))
        self.assertEqual(response.status_code, 302)


class HealthReportGenerateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_generate_report_with_data(self):
        """generate_from_data should create a report with blood test data."""
        BloodTest.objects.create(
            test_name='Hemoglobin', value=10, unit='g/dL',
            date=date.today(), normal_min=13.8, normal_max=17.2,
        )
        report = HealthReport.generate_from_data(
            'monthly', date.today() - timedelta(days=30), date.today(),
        )
        self.assertIn('Blood Tests', report.content)
        self.assertIn('out of normal range', report.content)

    def test_generate_report_empty_data(self):
        """generate_from_data should handle no data gracefully."""
        report = HealthReport.generate_from_data(
            'monthly', date.today() - timedelta(days=30), date.today(),
        )
        self.assertIn('No health data found', report.content)

    def test_generate_endpoint(self):
        """Generate endpoint should create a report and redirect."""
        response = self.client.post(reverse('health_report_generate'), {
            'report_type': 'monthly',
            'period_start': (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'period_end': date.today().strftime('%Y-%m-%d'),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HealthReport.objects.count(), 1)


class PredictiveBiomarkerGenerateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_generate_prediction_from_history(self):
        """Should generate a prediction from 2+ blood test data points."""
        BloodTest.objects.create(
            test_name='Glucose', value=90, unit='mg/dL',
            date=date.today() - timedelta(days=60),
        )
        BloodTest.objects.create(
            test_name='Glucose', value=95, unit='mg/dL',
            date=date.today() - timedelta(days=30),
        )
        prediction = PredictiveBiomarker.generate_from_history(
            'Glucose', date.today() + timedelta(days=30),
        )
        self.assertIsNotNone(prediction)
        self.assertGreater(prediction.predicted_value, 0)
        self.assertIsNotNone(prediction.confidence_percent)

    def test_generate_prediction_insufficient_data(self):
        """Should return None with less than 2 data points."""
        BloodTest.objects.create(
            test_name='Glucose', value=90, unit='mg/dL',
            date=date.today(),
        )
        prediction = PredictiveBiomarker.generate_from_history(
            'Glucose', date.today() + timedelta(days=30),
        )
        self.assertIsNone(prediction)

    def test_generate_endpoint(self):
        """Generate endpoint should redirect."""
        response = self.client.post(reverse('predictive_biomarker_generate'), {
            'biomarker_name': 'Glucose',
            'prediction_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
        })
        self.assertEqual(response.status_code, 302)


class BiologicalAgeEstimateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_estimate_from_health_data(self):
        """Should estimate biological age from available health data."""
        VitalSign.objects.create(
            date=date.today(), systolic_bp=150, heart_rate=85, spo2=97,
        )
        calc = BiologicalAgeCalculation.estimate_from_health_data(40)
        self.assertIsNotNone(calc)
        self.assertEqual(calc.method, 'health_data_estimate')
        self.assertNotEqual(calc.biological_age, 40)

    def test_estimate_no_data(self):
        """Should return None when no health data available."""
        calc = BiologicalAgeCalculation.estimate_from_health_data(40)
        self.assertIsNone(calc)

    def test_estimate_endpoint(self):
        """Estimate endpoint should redirect."""
        VitalSign.objects.create(date=date.today(), systolic_bp=120)
        response = self.client.post(reverse('biological_age_estimate'), {
            'chronological_age': '40',
        })
        self.assertEqual(response.status_code, 302)


class IntegrationConfigActivateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')

    def test_activate_with_config(self):
        """Should activate when configuration is provided."""
        config = IntegrationConfig.objects.create(
            category='ehr', feature_type='data_sync',
            configuration={'api_key': 'test123'},
        )
        success, msg = config.activate()
        self.assertTrue(success)
        config.refresh_from_db()
        self.assertTrue(config.is_enabled)

    def test_activate_without_config(self):
        """Should fail to activate when configuration is empty."""
        config = IntegrationConfig.objects.create(
            category='ehr', feature_type='data_sync',
        )
        success, msg = config.activate()
        self.assertFalse(success)
        config.refresh_from_db()
        self.assertFalse(config.is_enabled)

    def test_run_integration(self):
        """Should update last_run timestamp."""
        config = IntegrationConfig.objects.create(
            category='ehr', feature_type='data_sync',
            configuration={'api_key': 'test123'}, is_enabled=True,
        )
        success, msg = config.run_integration()
        self.assertTrue(success)
        config.refresh_from_db()
        self.assertIsNotNone(config.last_run)

    def test_run_disabled_integration(self):
        """Should fail to run when not enabled."""
        config = IntegrationConfig.objects.create(
            category='ehr', feature_type='data_sync',
        )
        success, msg = config.run_integration()
        self.assertFalse(success)

    def test_activate_endpoint(self):
        """Activate endpoint should redirect."""
        config = IntegrationConfig.objects.create(
            category='ehr', feature_type='data_sync',
            configuration={'api_key': 'test123'},
        )
        response = self.client.post(reverse('integration_config_activate', kwargs={'pk': config.pk}))
        self.assertEqual(response.status_code, 302)

    def test_run_endpoint(self):
        """Run endpoint should redirect."""
        config = IntegrationConfig.objects.create(
            category='ehr', feature_type='data_sync',
            configuration={'api_key': 'test123'}, is_enabled=True,
        )
        response = self.client.post(reverse('integration_config_run', kwargs={'pk': config.pk}))
        self.assertEqual(response.status_code, 302)


# ===== Enhanced List View Tests =====

class SleepListEnhancedTests(TestCase):
    """Tests for enhanced sleep list view with pagination, filtering, and stats."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        for i in range(25):
            SleepLog.objects.create(
                date=date(2026, 1, 1) + timedelta(days=i),
                total_sleep_minutes=420 + i,
                deep_sleep_minutes=90 + i,
                sleep_quality_score=60 + i,
            )

    def test_sleep_list_has_pagination(self):
        response = self.client.get(reverse('sleep_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context['page_obj'].paginator.count, 25)
        self.assertEqual(len(response.context['page_obj']), 20)

    def test_sleep_list_page_2(self):
        response = self.client.get(reverse('sleep_list'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj']), 5)

    def test_sleep_list_has_stats(self):
        response = self.client.get(reverse('sleep_list'))
        self.assertIn('stats', response.context)
        self.assertEqual(response.context['stats']['total_entries'], 25)
        self.assertIsNotNone(response.context['stats']['avg_total_sleep'])
        self.assertIsNotNone(response.context['stats']['avg_quality'])

    def test_sleep_list_date_filtering(self):
        response = self.client.get(reverse('sleep_list'), {
            'start_date': '2026-01-10',
            'end_date': '2026-01-15',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 6)

    def test_sleep_list_date_filtering_start_only(self):
        response = self.client.get(reverse('sleep_list'), {'start_date': '2026-01-20'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 6)

    def test_sleep_list_has_chart_data(self):
        response = self.client.get(reverse('sleep_list'))
        self.assertIn('chart_dates', response.context)
        self.assertIn('chart_quality', response.context)
        self.assertIn('chart_total', response.context)

    def test_sleep_list_renders_summary_stats(self):
        response = self.client.get(reverse('sleep_list'))
        self.assertContains(response, 'Avg Sleep (min)')
        self.assertContains(response, 'Avg Quality Score')

    def test_sleep_list_renders_filter_form(self):
        response = self.client.get(reverse('sleep_list'))
        self.assertContains(response, 'startDate')
        self.assertContains(response, 'endDate')

    def test_sleep_list_renders_trend_chart(self):
        response = self.client.get(reverse('sleep_list'))
        self.assertContains(response, 'sleepTrendChart')


class HydrationListEnhancedTests(TestCase):
    """Tests for enhanced hydration list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        for i in range(25):
            HydrationLog.objects.create(
                date=date(2026, 1, 1) + timedelta(days=i),
                fluid_intake_ml=2000 + i * 50,
                goal_ml=2500,
            )

    def test_hydration_list_has_pagination(self):
        response = self.client.get(reverse('hydration_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 25)
        self.assertEqual(len(response.context['page_obj']), 20)

    def test_hydration_list_has_stats(self):
        response = self.client.get(reverse('hydration_list'))
        stats = response.context['stats']
        self.assertEqual(stats['total_entries'], 25)
        self.assertIsNotNone(stats['avg_intake'])
        self.assertIsNotNone(stats['avg_goal_pct'])
        self.assertIsNotNone(stats['days_goal_met'])

    def test_hydration_list_date_filtering(self):
        response = self.client.get(reverse('hydration_list'), {
            'start_date': '2026-01-10',
            'end_date': '2026-01-15',
        })
        self.assertEqual(response.context['page_obj'].paginator.count, 6)

    def test_hydration_list_renders_summary(self):
        response = self.client.get(reverse('hydration_list'))
        self.assertContains(response, 'Avg Daily Intake')
        self.assertContains(response, 'Days Goal Met')

    def test_hydration_list_renders_chart(self):
        response = self.client.get(reverse('hydration_list'))
        self.assertContains(response, 'hydrationTrendChart')


class BodyCompositionListEnhancedTests(TestCase):
    """Tests for enhanced body composition list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        for i in range(5):
            BodyComposition.objects.create(
                date=date(2026, 1, 1) + timedelta(days=i * 7),
                body_fat_percentage=18.0 + i * 0.5,
                skeletal_muscle_mass=35.0 + i * 0.2,
                waist_circumference=80 + i,
                hip_circumference=100,
            )

    def test_body_composition_list_has_stats(self):
        response = self.client.get(reverse('body_composition_list'))
        self.assertEqual(response.status_code, 200)
        stats = response.context['stats']
        self.assertEqual(stats['total_entries'], 5)
        self.assertIsNotNone(stats['avg_body_fat'])
        self.assertIsNotNone(stats['avg_muscle_mass'])

    def test_body_composition_list_date_filtering(self):
        response = self.client.get(reverse('body_composition_list'), {
            'start_date': '2026-01-01',
            'end_date': '2026-01-14',
        })
        self.assertEqual(response.context['page_obj'].paginator.count, 2)

    def test_body_composition_list_has_chart_data(self):
        response = self.client.get(reverse('body_composition_list'))
        self.assertIn('chart_dates', response.context)
        self.assertIn('chart_body_fat', response.context)
        self.assertIn('chart_muscle', response.context)

    def test_body_composition_list_renders_stats(self):
        response = self.client.get(reverse('body_composition_list'))
        self.assertContains(response, 'Avg Body Fat')
        self.assertContains(response, 'Avg Muscle Mass')


class MedicationScheduleListEnhancedTests(TestCase):
    """Tests for enhanced medication schedule list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        MedicationSchedule.objects.create(
            medication_name='Aspirin', dosage='100mg', frequency='Daily',
            start_date=date(2026, 1, 1), is_active=True,
        )
        MedicationSchedule.objects.create(
            medication_name='Ibuprofen', dosage='200mg', frequency='As needed',
            start_date=date(2026, 1, 1), is_active=False,
        )
        MedicationSchedule.objects.create(
            medication_name='Vitamin D', dosage='1000IU', frequency='Daily',
            start_date=date(2026, 1, 1), is_active=True,
        )

    def test_medication_list_has_search(self):
        response = self.client.get(reverse('medication_schedule_list'), {'q': 'Aspirin'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_medication_list_filter_active(self):
        response = self.client.get(reverse('medication_schedule_list'), {'status': 'active'})
        self.assertEqual(response.context['page_obj'].paginator.count, 2)

    def test_medication_list_filter_inactive(self):
        response = self.client.get(reverse('medication_schedule_list'), {'status': 'inactive'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_medication_list_has_summary_counts(self):
        response = self.client.get(reverse('medication_schedule_list'))
        self.assertEqual(response.context['total_count'], 3)
        self.assertEqual(response.context['total_active'], 2)

    def test_medication_list_renders_search_form(self):
        response = self.client.get(reverse('medication_schedule_list'))
        self.assertContains(response, 'searchQuery')
        self.assertContains(response, 'statusFilter')

    def test_medication_list_has_pagination(self):
        response = self.client.get(reverse('medication_schedule_list'))
        self.assertIn('page_obj', response.context)


class HealthGoalListEnhancedTests(TestCase):
    """Tests for enhanced health goal list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        HealthGoal.objects.create(
            title='Lose Weight', target_value=70, current_value=65,
            unit='kg', status='active', start_date=date(2026, 1, 1),
        )
        HealthGoal.objects.create(
            title='Run 5K', target_value=5, current_value=5,
            unit='km', status='completed', start_date=date(2026, 1, 1),
        )
        HealthGoal.objects.create(
            title='Sleep 8 hours', target_value=8, current_value=6,
            unit='hours', status='paused', start_date=date(2026, 1, 1),
        )

    def test_health_goal_list_has_stats(self):
        response = self.client.get(reverse('health_goal_list'))
        self.assertEqual(response.status_code, 200)
        stats = response.context['stats']
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['in_progress'], 1)
        self.assertEqual(stats['paused'], 1)

    def test_health_goal_list_filter_by_status(self):
        response = self.client.get(reverse('health_goal_list'), {'status': 'active'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_health_goal_list_search_by_title(self):
        response = self.client.get(reverse('health_goal_list'), {'q': 'Weight'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_health_goal_list_completion_rate(self):
        response = self.client.get(reverse('health_goal_list'))
        stats = response.context['stats']
        self.assertAlmostEqual(stats['completion_rate'], 33.3, places=1)

    def test_health_goal_list_renders_stats(self):
        response = self.client.get(reverse('health_goal_list'))
        self.assertContains(response, 'Completion Rate')
        self.assertContains(response, 'Active')  # replaces 'In Progress'

    def test_health_goal_list_has_pagination(self):
        response = self.client.get(reverse('health_goal_list'))
        self.assertIn('page_obj', response.context)


class MacroListEnhancedTests(TestCase):
    """Tests for enhanced macronutrient list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.client.login(username='testuser', password='testpass123')
        for i in range(25):
            MacronutrientLog.objects.create(
                date=date(2026, 1, 1) + timedelta(days=i),
                protein_grams=120 + i,
                carbohydrate_grams=200 + i,
                fat_grams=60 + i,
                calories=2000 + i * 20,
                fiber_grams=25 + i,
            )

    def test_macro_list_has_pagination(self):
        response = self.client.get(reverse('macro_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 25)
        self.assertEqual(len(response.context['page_obj']), 20)

    def test_macro_list_has_stats(self):
        response = self.client.get(reverse('macro_list'))
        stats = response.context['stats']
        self.assertEqual(stats['total_entries'], 25)
        self.assertIsNotNone(stats['avg_protein'])
        self.assertIsNotNone(stats['avg_carbs'])
        self.assertIsNotNone(stats['avg_fat'])
        self.assertIsNotNone(stats['avg_calories'])

    def test_macro_list_date_filtering(self):
        response = self.client.get(reverse('macro_list'), {
            'start_date': '2026-01-10',
            'end_date': '2026-01-15',
        })
        self.assertEqual(response.context['page_obj'].paginator.count, 6)

    def test_macro_list_renders_summary(self):
        response = self.client.get(reverse('macro_list'))
        self.assertContains(response, 'Avg Calories')
        self.assertContains(response, 'Avg Protein')
        self.assertContains(response, 'Avg Carbs')

    def test_macro_list_has_chart_data(self):
        response = self.client.get(reverse('macro_list'))
        self.assertIn('chart_dates', response.context)
        self.assertIn('chart_protein', response.context)
        self.assertIn('chart_calories', response.context)

    def test_macro_list_renders_chart(self):
        response = self.client.get(reverse('macro_list'))
        self.assertContains(response, 'macroTrendChart')
