from django.test import TestCase, Client
from django.urls import reverse
from tracker.models import BloodTest, BloodTestInfo, VitalSign
from datetime import date


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
