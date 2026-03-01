from django.test import TestCase, Client
from django.urls import reverse
from tracker.models import BloodTest, BloodTestInfo, VitalSign
from datetime import date


class TemplateFilterTests(TestCase):
    def test_tojson_filter(self):
        from tracker.templatetags.json_filters import tojson
        self.assertEqual(tojson([1, 2, 3]), '[1, 2, 3]')
        self.assertEqual(tojson({"key": "value"}), '{"key": "value"}')

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
