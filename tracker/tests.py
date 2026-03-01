from django.test import TestCase, Client
from django.urls import reverse
from tracker.models import BloodTest, BloodTestInfo, VitalSign, DataPointAnnotation, DashboardWidget
from datetime import date
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


# ===== Phase 2 Tests =====

from tracker.models import (
    BodyComposition, HydrationLog, EnergyFatigueLog,
    CustomVitalDefinition, CustomVitalEntry, PainLog,
    RestingMetabolicRate, OrthostaticReading, ReproductiveHealthLog,
    SymptomJournal, MetabolicLog, KetoneLog,
)


class Phase2ModelTests(TestCase):
    """Test model creation, __str__, and calculated fields for Phase 2 models."""

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
    """Test GET requests return 200 for all Phase 2 list and add pages."""

    def setUp(self):
        self.client = Client()

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
    """Test POST create, edit, and delete for each Phase 2 module."""

    def setUp(self):
        self.client = Client()

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
    """Phase 3: Dark mode toggle and theme infrastructure."""

    def setUp(self):
        self.client = Client()

    def test_base_template_has_dark_mode_toggle(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'dark-mode-toggle')

    def test_base_template_has_data_theme_attribute(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'data-theme=')

    def test_phase3_css_loaded(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'css/phase3.css')

    def test_phase3_js_loaded(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'js/phase3.js')


class Phase3NavigationTests(TestCase):
    """Phase 3: Sidebar navigation system."""

    def setUp(self):
        self.client = Client()

    def test_sidebar_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'sidebar')
        self.assertContains(response, 'sidebar-toggle')

    def test_sidebar_has_categories(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'sidebar-category')
        self.assertContains(response, 'Body &amp; Metrics')
        self.assertContains(response, 'Charts &amp; Visualizations')
        self.assertContains(response, 'Health Tracking')
        self.assertContains(response, 'Data Management')

    def test_sidebar_has_all_nav_links(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Vitals')
        self.assertContains(response, 'History')
        self.assertContains(response, 'Body Composition')
        self.assertContains(response, 'Hydration')
        self.assertContains(response, 'Pain Mapping')


class Phase3AccessibilityTests(TestCase):
    """Phase 3: WCAG 2.1 AA compliance features."""

    def setUp(self):
        self.client = Client()

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
    """Phase 3: Quick-entry vitals modal."""

    def setUp(self):
        self.client = Client()

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
    """Phase 3: Progressive Web App features."""

    def setUp(self):
        self.client = Client()

    def test_manifest_link_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'manifest.json')

    def test_theme_color_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'theme-color')

    def test_service_worker_js_registered(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'js/phase3.js')


class Phase3GlobalSearchTests(TestCase):
    """Phase 3: Global search API."""

    def setUp(self):
        self.client = Client()
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
    """Phase 3: Medical tooltips on forms and labels."""

    def setUp(self):
        self.client = Client()

    def test_tooltips_on_quick_entry(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'data-medical-tooltip')

    def test_tooltip_content_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Blood oxygen saturation')
        self.assertContains(response, 'Resting heart rate')


class Phase3VoiceInputTests(TestCase):
    """Phase 3: Voice-to-text integration."""

    def setUp(self):
        self.client = Client()

    def test_voice_button_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'voice-input-btn')

    def test_voice_button_has_aria(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'aria-label="Voice search"')


class Phase3OnboardingTests(TestCase):
    """Phase 3: Onboarding tour button."""

    def setUp(self):
        self.client = Client()

    def test_tour_button_present(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'start-tour-btn')

    def test_tour_button_has_label(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Start guided tour')
