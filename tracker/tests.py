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
