from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from .models import (
    BloodTest, BloodTestInfo, VitalSign, DataPointAnnotation, DashboardWidget,
    BodyComposition, HydrationLog, EnergyFatigueLog,
    CustomVitalDefinition, CustomVitalEntry, PainLog,
    RestingMetabolicRate, OrthostaticReading, ReproductiveHealthLog,
    SymptomJournal, MetabolicLog, KetoneLog, BODY_REGIONS,
    # Phase 5
    WearableDevice, WearableSyncLog, WEARABLE_PLATFORMS,
    # Phase 6
    SleepLog, CircadianRhythmLog, DreamJournal, MacronutrientLog,
    MicronutrientLog, FoodEntry, FastingLog, CaffeineAlcoholLog,
    # Phase 7
    UserProfile, FamilyAccount, EncryptionKey, AuditLog,
    APIRateLimitConfig, ConsentLog, TenantConfig, AdminTelemetry,
    AnonymizedDataReport, DatabaseScalingConfig, BackupConfiguration,
    # Phase 8
    PredictiveBiomarker, HealthReport, ClinicalTrialMatch,
    BiologicalAgeCalculation, MedicationSchedule, PharmacologicalInteraction,
    HealthGoal, CriticalAlert,
    # Phase 9
    SecureViewingLink, PractitionerAccess, IntakeSummary,
    DataExportRequest, StakeholderEmail,
    # Phase 10-12
    IntegrationConfig, IntegrationSubTask,
    INTEGRATION_CATEGORIES, INTEGRATION_FEATURE_TYPES,
)
from .generic_crud import make_crud_views
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
import csv
import os
import io
import json
import re
from django.http import HttpResponse, JsonResponse
from django.db.models import Q as models_Q, Avg, Sum, Count
from django.core.paginator import Paginator

@login_required
def index(request):
    tests = BloodTest.objects.all().order_by('-date')
    test_types = set(test.test_name for test in tests)

    total_tests = len(tests)
    out_of_range = sum(1 for test in tests if test.normal_min is not None and test.normal_max is not None and not (test.normal_min <= test.value <= test.normal_max))
    latest_vitals = VitalSign.objects.all().order_by('-date').first()

    bars = {}
    tests_by_category = {}

    for test in tests:
        cat = test.category or 'Uncategorized'
        if cat not in tests_by_category:
            tests_by_category[cat] = []
        tests_by_category[cat].append(test)

    for test in tests:
        if test.normal_min is not None and test.normal_max is not None:
            normal_range = test.normal_max - test.normal_min
            if normal_range == 0:
                normal_range = 1.0

            abs_min = min(test.normal_min - normal_range, test.value - normal_range * 0.2)
            if abs_min < 0 and test.normal_min >= 0:
                abs_min = 0

            abs_max = max(test.normal_max + normal_range, test.value + normal_range * 0.2)
            total_range = abs_max - abs_min
            if total_range == 0:
                total_range = 1.0

            low_width = max(0, ((test.normal_min - abs_min) / total_range) * 100)
            normal_width = max(0, ((test.normal_max - test.normal_min) / total_range) * 100)
            high_width = max(0, ((abs_max - test.normal_max) / total_range) * 100)

            total_width = low_width + normal_width + high_width
            if total_width > 0:
                low_width = (low_width / total_width) * 100
                normal_width = (normal_width / total_width) * 100
                high_width = (high_width / total_width) * 100

            value_pos = max(0, min(100, ((test.value - abs_min) / total_range) * 100))

            bars[test.id] = {
                'low_width': low_width,
                'normal_width': normal_width,
                'high_width': high_width,
                'value_pos': value_pos,
                'value': test.value,
                'unit': test.unit
            }

    context = {
        'tests': tests,
        'test_types': test_types,
        'bars': bars,
        'total_tests': total_tests,
        'out_of_range': out_of_range,
        'latest_vitals': latest_vitals,
        'tests_by_category': tests_by_category,
        'widgets': _get_dashboard_widgets(),
    }
    return render(request, 'index.html', context)


@login_required
def history(request):
    tests = BloodTest.objects.all().order_by('-date')
    vitals = VitalSign.objects.all().order_by('-date')

    history_items = []
    for test in tests:
        history_items.append({
            'type': 'Blood Test',
            'date': test.date,
            'name': test.test_name,
            'value': f"{test.value} {test.unit}",
            'notes': f"Range: {test.normal_min} - {test.normal_max} {test.unit}" if test.normal_min is not None and test.normal_max is not None else "",
            'status': 'Normal' if test.normal_min is not None and test.normal_max is not None and test.normal_min <= test.value <= test.normal_max else ('Out of Range' if test.normal_min is not None and test.normal_max is not None else 'N/A')
        })

    for vital in vitals:
        bp_str = f"{vital.systolic_bp}/{vital.diastolic_bp} mmHg" if vital.systolic_bp is not None and vital.diastolic_bp is not None else ""
        hr_str = f"{vital.heart_rate} bpm" if vital.heart_rate is not None else ""
        weight_str = f"{vital.weight} kg" if vital.weight is not None else ""
        bbt_str = f"BBT: {vital.bbt}°C" if vital.bbt is not None else ""
        spo2_str = f"SpO2: {vital.spo2}%" if vital.spo2 is not None else ""
        rr_str = f"RR: {vital.respiratory_rate}/min" if vital.respiratory_rate is not None else ""

        details = [val for val in [weight_str, hr_str, bp_str, bbt_str, spo2_str, rr_str] if val]

        history_items.append({
            'type': 'Vitals',
            'date': vital.date,
            'name': 'Vital Signs',
            'value': ", ".join(details),
            'notes': '',
            'status': 'N/A'
        })

    history_items.sort(key=lambda x: x['date'], reverse=True)

    return render(request, 'history.html', {'history': history_items})


@login_required
def vitals(request):
    all_vitals = VitalSign.objects.all().order_by('-date')
    return render(request, 'vitals.html', {'vitals': all_vitals})

@login_required
def add_test(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        test_names = request.POST.getlist('test_names')

        if not date_str or not test_names:
            messages.error(request, 'Please select a date and at least one blood test.')
            return redirect('add_test')

        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        tests_added = 0

        for test_name in test_names:
            value = request.POST.get(f'values[{test_name}]')
            if not value:
                messages.warning(request, f'No value provided for {test_name}.')
                continue

            try:
                value = float(value)
            except ValueError:
                messages.error(request, f'Invalid value for {test_name}. Please enter a numeric value.')
                continue

            test_info = BloodTestInfo.objects.filter(test_name=test_name).first()
            if not test_info:
                messages.error(request, f'Test "{test_name}" not found in system.')
                continue

            BloodTest.objects.create(
                test_name=test_name,
                value=value,
                unit=test_info.unit,
                date=date,
                normal_min=test_info.normal_min,
                normal_max=test_info.normal_max,
                category=test_info.category or 'Uncategorized'
            )
            tests_added += 1

        if tests_added > 0:
            messages.success(request, f'{tests_added} blood test(s) added successfully!')
        else:
            messages.warning(request, 'No tests were added. Please provide valid values for the selected tests.')
        return redirect('index')

    else:
        test_info_objects = BloodTestInfo.objects.all()
        test_info = {ti.test_name: {'unit': ti.unit, 'normal_min': ti.normal_min, 'normal_max': ti.normal_max, 'category': ti.category} for ti in test_info_objects}
        return render(request, 'add.html', {'test_info': test_info, 'date': datetime.now().strftime('%Y-%m-%d')})

@login_required
def add_test_info(request):
    if request.method == 'POST':
        test_name = request.POST.get('test_name')
        unit = request.POST.get('unit')
        normal_min_str = request.POST.get('normal_min')
        normal_max_str = request.POST.get('normal_max')
        category = request.POST.get('category', 'Uncategorized')

        if not test_name or not unit or not normal_min_str or not normal_max_str:
            messages.error(request, 'Please fill out all fields.')
            return redirect('add_test_info')

        try:
            normal_min = float(normal_min_str)
            normal_max = float(normal_max_str)
        except ValueError:
            messages.error(request, 'Normal Min and Max must be numeric.')
            return redirect('add_test_info')

        # Also append to csv logic ported
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'blood_tests.csv')
        try:
            with open(csv_path, mode='a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([test_name, unit, normal_min, normal_max, category])
        except Exception as e:
            pass # Non-critical if CSV update fails, DB is truth

        BloodTestInfo.objects.create(
            test_name=test_name,
            unit=unit,
            normal_min=normal_min,
            normal_max=normal_max,
            category=category
        )

        messages.success(request, 'New blood test info added successfully!')
        return redirect('add_test')

    return render(request, 'add_test_info.html')

@login_required
def delete_test(request, test_id):
    if request.method == 'POST':
        test = get_object_or_404(BloodTest, id=test_id)
        test.delete()
        messages.success(request, 'Blood test deleted successfully!')
    return redirect('index')

@login_required
def edit_test(request, test_id):
    test = get_object_or_404(BloodTest, id=test_id)

    if request.method == 'POST':
        value = request.POST.get('value')
        date_str = request.POST.get('date')

        try:
            test.value = float(value)
            test.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            test.save()
            messages.success(request, 'Blood test updated successfully!')
            return redirect('index')
        except Exception as e:
            messages.error(request, 'Error updating blood test. Please try again.')
            return redirect('edit_test', test_id=test.id)

    return render(request, 'edit.html', {'test': test})

@login_required
def add_vitals(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        weight = request.POST.get('weight')
        heart_rate = request.POST.get('heart_rate')
        systolic_bp = request.POST.get('systolic_bp')
        diastolic_bp = request.POST.get('diastolic_bp')
        bbt = request.POST.get('bbt')
        spo2 = request.POST.get('spo2')
        respiratory_rate = request.POST.get('respiratory_rate')

        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('add_vitals')

        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        try:
            VitalSign.objects.create(
                date=date,
                weight=float(weight) if weight else None,
                heart_rate=int(heart_rate) if heart_rate else None,
                systolic_bp=int(systolic_bp) if systolic_bp else None,
                diastolic_bp=int(diastolic_bp) if diastolic_bp else None,
                bbt=float(bbt) if bbt else None,
                spo2=float(spo2) if spo2 else None,
                respiratory_rate=int(respiratory_rate) if respiratory_rate else None,
            )
            messages.success(request, 'Vital signs added successfully!')
            return redirect('vitals')
        except Exception as e:
            messages.error(request, 'Error adding vital signs. Please try again.')
            return redirect('add_vitals')

    return render(request, 'add_vitals.html', {'date': datetime.now().strftime('%Y-%m-%d')})

@login_required
def edit_vitals(request, vital_id):
    vital = get_object_or_404(VitalSign, id=vital_id)

    if request.method == 'POST':
        date_str = request.POST.get('date')
        weight = request.POST.get('weight')
        heart_rate = request.POST.get('heart_rate')
        systolic_bp = request.POST.get('systolic_bp')
        diastolic_bp = request.POST.get('diastolic_bp')
        bbt = request.POST.get('bbt')
        spo2 = request.POST.get('spo2')
        respiratory_rate = request.POST.get('respiratory_rate')

        try:
            vital.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            vital.weight = float(weight) if weight else None
            vital.heart_rate = int(heart_rate) if heart_rate else None
            vital.systolic_bp = int(systolic_bp) if systolic_bp else None
            vital.diastolic_bp = int(diastolic_bp) if diastolic_bp else None
            vital.bbt = float(bbt) if bbt else None
            vital.spo2 = float(spo2) if spo2 else None
            vital.respiratory_rate = int(respiratory_rate) if respiratory_rate else None
            vital.save()

            messages.success(request, 'Vital signs updated successfully!')
            return redirect('vitals')
        except Exception as e:
            messages.error(request, 'Error updating vital signs. Please try again.')
            return redirect('edit_vitals', vital_id=vital.id)

    return render(request, 'edit_vitals.html', {'vital': vital})

@login_required
def delete_vitals(request, vital_id):
    if request.method == 'POST':
        vital = get_object_or_404(VitalSign, id=vital_id)
        vital.delete()
        messages.success(request, 'Vital sign deleted successfully!')
    return redirect('vitals')

@login_required
def chart(request, test_name):
    tests = BloodTest.objects.filter(test_name=test_name).order_by('date')
    dates = [test.date.strftime('%Y-%m-%d') for test in tests]
    values = [test.value for test in tests]
    annotations_map = {}
    for test in tests:
        annots = list(test.annotations.all().values('id', 'note', 'created_at'))
        if annots:
            annotations_map[test.date.strftime('%Y-%m-%d')] = [
                {'id': a['id'], 'note': a['note']} for a in annots
            ]
    return render(request, 'chart.html', {
        'dates': dates, 'values': values, 'test_name': test_name,
        'tests': tests, 'annotations_map': annotations_map,
    })

@login_required
def blood_tests_charts(request):
    tests = BloodTest.objects.all().order_by('date')
    charts_data = {}
    for test in tests:
        if test.test_name not in charts_data:
            charts_data[test.test_name] = {
                'unit': test.unit,
                'data': [],
                'normal_min': test.normal_min,
                'normal_max': test.normal_max
            }
        charts_data[test.test_name]['data'].append({
            'x': test.date.strftime('%Y-%m-%d'),
            'y': test.value
        })

    return render(request, 'blood_charts.html', {'charts_data': charts_data})

@login_required
def blood_tests_boxplots(request):
    tests = BloodTest.objects.all().order_by('date')
    boxplots_data = {}
    for test in tests:
        if test.test_name not in boxplots_data:
            boxplots_data[test.test_name] = {
                'unit': test.unit,
                'data': [],
                'normal_min': test.normal_min,
                'normal_max': test.normal_max
            }
        boxplots_data[test.test_name]['data'].append(test.value)

    return render(request, 'blood_boxplots.html', {'boxplots_data': boxplots_data})

@login_required
def comparative_bar_charts(request):
    tests = BloodTest.objects.all().order_by('-date')
    latest_tests = {}
    for test in tests:
        if test.test_name not in latest_tests:
            if test.normal_min is not None and test.normal_max is not None:
                latest_tests[test.test_name] = test

    return render(request, 'comparative_bar_charts.html', {'latest_tests': latest_tests})

@login_required
def vitals_charts(request):
    vitals = VitalSign.objects.all().order_by('date')
    weight_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.weight} for v in vitals if v.weight is not None]
    hr_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.heart_rate} for v in vitals if v.heart_rate is not None]
    sys_bp_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.systolic_bp} for v in vitals if v.systolic_bp is not None]
    dia_bp_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.diastolic_bp} for v in vitals if v.diastolic_bp is not None]
    bbt_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.bbt} for v in vitals if v.bbt is not None]
    spo2_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.spo2} for v in vitals if v.spo2 is not None]
    rr_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.respiratory_rate} for v in vitals if v.respiratory_rate is not None]

    return render(request, 'vitals_charts.html', {
        'weight_data': weight_data,
        'hr_data': hr_data,
        'sys_bp_data': sys_bp_data,
        'dia_bp_data': dia_bp_data,
        'bbt_data': bbt_data,
        'spo2_data': spo2_data,
        'rr_data': rr_data,
    })

@login_required
def scatter_plots(request):
    tests = BloodTest.objects.all().order_by('date')
    vitals = VitalSign.objects.all().order_by('date')

    # Build a dict of metric_name -> list of {date, value}
    metrics = {}

    for test in tests:
        key = test.test_name
        if key not in metrics:
            metrics[key] = []
        metrics[key].append({
            'date': test.date.strftime('%Y-%m-%d'),
            'value': test.value
        })

    vital_fields = [
        ('Weight', 'weight'),
        ('Heart Rate', 'heart_rate'),
        ('Systolic BP', 'systolic_bp'),
        ('Diastolic BP', 'diastolic_bp'),
    ]
    for label, field in vital_fields:
        for v in vitals:
            val = getattr(v, field)
            if val is not None:
                if label not in metrics:
                    metrics[label] = []
                metrics[label].append({
                    'date': v.date.strftime('%Y-%m-%d'),
                    'value': float(val)
                })

    metric_names = sorted(metrics.keys())

    return render(request, 'scatter_plots.html', {
        'metrics': metrics,
        'metric_names': metric_names,
    })

import pdfplumber
import pdf2image
import pytesseract
from thefuzz import process, fuzz

@login_required
def import_data(request):
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'No file part')
            return redirect('import_data')
        file = request.FILES['file']
        if file.name == '':
            messages.error(request, 'No selected file')
            return redirect('import_data')

        allowed_extensions = ('.csv', '.json', '.pdf', '.hl7')
        if not file.name.lower().endswith(allowed_extensions):
            messages.error(request, 'Please upload a .csv, .json, .pdf, or .hl7 file')
            return redirect('import_data')

        try:
            file_data = []

            if file.name.lower().endswith('.csv'):
                file_content = file.read().decode("UTF8")
                stream = io.StringIO(file_content, newline=None)
                csv_input = csv.DictReader(stream)
                file_data = list(csv_input)
            elif file.name.lower().endswith('.json'):
                json_data = json.load(file)
                if isinstance(json_data, dict) and json_data.get('resourceType') == 'Bundle':
                    for entry in json_data.get('entry', []):
                        obs = entry.get('resource', {})
                        if obs.get('resourceType') == 'Observation':
                            name = obs.get('code', {}).get('text')
                            if not name:
                                codings = obs.get('code', {}).get('coding', [])
                                if codings:
                                    name = codings[0].get('display')

                            val_quantity = obs.get('valueQuantity', {})
                            val = val_quantity.get('value')
                            unit = val_quantity.get('unit')

                            date_str = obs.get('effectiveDateTime')
                            date_obj = date_str[:10] if date_str else None

                            ref_ranges = obs.get('referenceRange', [])
                            normal_min = None
                            normal_max = None
                            if ref_ranges:
                                normal_min = ref_ranges[0].get('low', {}).get('value')
                                normal_max = ref_ranges[0].get('high', {}).get('value')

                            is_vital = False
                            categories = obs.get('category', [])
                            for cat in categories:
                                codings = cat.get('coding', [])
                                for c in codings:
                                    if c.get('code') == 'vital-signs':
                                        is_vital = True

                            if is_vital:
                                if name and "Blood Pressure" in name and "component" in obs:
                                    sys = None
                                    dia = None
                                    for comp in obs['component']:
                                        c_name = comp.get('code', {}).get('text', '').lower()
                                        c_val = comp.get('valueQuantity', {}).get('value')
                                        if 'systolic' in c_name:
                                            sys = c_val
                                        elif 'diastolic' in c_name:
                                            dia = c_val
                                    if sys and dia:
                                        file_data.append({
                                            "Date": date_obj,
                                            "Type": "Vitals",
                                            "Value": f"{sys}/{dia} mmHg"
                                        })
                                else:
                                    file_data.append({
                                        "Date": date_obj,
                                        "Type": "Vitals",
                                        "Value": f"{val} {unit}"
                                    })
                            else:
                                if name and val is not None and date_obj:
                                    file_data.append({
                                        "Date": date_obj,
                                        "Type": "Blood Test",
                                        "Name": name,
                                        "Value": val,
                                        "Unit": unit,
                                        "Normal Min": normal_min,
                                        "Normal Max": normal_max
                                    })
                else:
                    file_data = json_data
                    if not isinstance(file_data, list):
                        messages.error(request, 'JSON file must contain a list of objects or be a FHIR Bundle.')
                        return redirect('import_data')
            elif file.name.lower().endswith('.hl7'):
                hl7_text = file.read().decode("UTF8")
                lines = hl7_text.replace('\r', '\n').split('\n')
                current_date = None
                for line in lines:
                    fields = line.split('|')
                    if fields[0] == 'OBR' and len(fields) > 7:
                        date_field = fields[7]
                        if date_field and len(date_field) >= 8:
                            current_date = f"{date_field[0:4]}-{date_field[4:6]}-{date_field[6:8]}"
                    elif fields[0] == 'OBX' and len(fields) > 5:
                        name_field = fields[3]
                        name = name_field.split('^')[1] if '^' in name_field else name_field
                        val = fields[5]
                        unit = fields[6] if len(fields) > 6 else ""
                        ref_range = fields[7] if len(fields) > 7 else ""

                        normal_min = None
                        normal_max = None
                        if '-' in ref_range:
                            try:
                                normal_min = float(ref_range.split('-')[0])
                                normal_max = float(ref_range.split('-')[1])
                            except ValueError:
                                pass

                        obs_date = current_date
                        if len(fields) > 14 and fields[14] and len(fields[14]) >= 8:
                            d = fields[14]
                            obs_date = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"

                        if not obs_date:
                            obs_date = datetime.now().date().strftime('%Y-%m-%d')

                        if name and val:
                            file_data.append({
                                "Date": obs_date,
                                "Type": "Blood Test",
                                "Name": name,
                                "Value": val,
                                "Unit": unit,
                                "Normal Min": normal_min,
                                "Normal Max": normal_max
                            })
            elif file.name.lower().endswith('.pdf'):
                pdf_bytes = file.read()
                text = ""

                try:
                    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"

                            tables = page.extract_tables()
                            for table in tables:
                                for row in table:
                                    row_text = " ".join([str(cell) for cell in row if cell])
                                    if row_text not in text:
                                        text += row_text + "\n"
                except Exception as e:
                    print(f"pdfplumber failed: {e}")

                if len(text.strip()) < 50:
                    text = ""
                    images = pdf2image.convert_from_bytes(pdf_bytes)
                    for img in images:
                        text += pytesseract.image_to_string(img) + "\n"

                date_match = re.search(r'(\d{4}-\d{2}-\d{2})|(\d{1,2}/\d{1,2}/\d{4})', text)
                pdf_date_str = None
                if date_match:
                    if date_match.group(1):
                        pdf_date_str = date_match.group(1)
                    else:
                        try:
                            pdf_date_str = datetime.strptime(date_match.group(2), "%m/%d/%Y").strftime("%Y-%m-%d")
                        except ValueError:
                            pass
                if not pdf_date_str:
                    pdf_date_str = datetime.now().date().strftime('%Y-%m-%d')

                db_test_names = list(BloodTestInfo.objects.values_list('test_name', flat=True))

                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    best_match = process.extractOne(line, db_test_names, scorer=fuzz.partial_ratio)

                    if best_match and best_match[1] > 85:
                        t_name = best_match[0]
                        if len(t_name) <= 3 and t_name not in line.split():
                            continue

                        nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                        if nums:
                            val = nums[0]

                            already_added = any(d.get("Name") == t_name for d in file_data)
                            if not already_added:
                                file_data.append({
                                    "Date": pdf_date_str,
                                    "Type": "Blood Test",
                                    "Name": t_name,
                                    "Value": val
                                })

            imported_tests = 0
            imported_vitals = 0
            skipped_rows = 0

            test_info_dict = {t.test_name: t for t in BloodTestInfo.objects.all()}

            for row in file_data:
                try:
                    date_str = row.get('Date')
                    if not date_str:
                        skipped_rows += 1
                        continue
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()

                    row_type = row.get('Type')

                    if row_type == 'Blood Test':
                        name = row.get('Name')
                        value_str = row.get('Value')
                        unit = row.get('Unit', '')
                        normal_min_str = row.get('Normal Min', '')
                        normal_max_str = row.get('Normal Max', '')

                        if not name or not value_str:
                            skipped_rows += 1
                            continue

                        value = float(value_str)
                        normal_min = float(normal_min_str) if normal_min_str else None
                        normal_max = float(normal_max_str) if normal_max_str else None

                        test_info = test_info_dict.get(name)
                        category = test_info.category if test_info else 'Uncategorized'

                        if test_info and test_info.unit:
                            final_unit = test_info.unit
                        else:
                            final_unit = unit

                        if test_info:
                            if normal_min is None and test_info.normal_min is not None:
                                normal_min = test_info.normal_min
                            if normal_max is None and test_info.normal_max is not None:
                                normal_max = test_info.normal_max

                        BloodTest.objects.create(
                            test_name=name,
                            value=value,
                            unit=final_unit,
                            date=date,
                            normal_min=normal_min,
                            normal_max=normal_max,
                            category=category
                        )
                        imported_tests += 1

                    elif row_type == 'Vitals':
                        value_str = row.get('Value', '')

                        weight = None
                        heart_rate = None
                        systolic_bp = None
                        diastolic_bp = None

                        parts = [p.strip() for p in value_str.split(',')]
                        for part in parts:
                            if 'kg' in part:
                                try:
                                    weight = float(part.replace('kg', '').strip())
                                except ValueError:
                                    pass
                            elif 'lbs' in part:
                                try:
                                    weight = float(part.replace('lbs', '').strip()) * 0.453592
                                except ValueError:
                                    pass
                            elif 'bpm' in part:
                                try:
                                    heart_rate = int(part.replace('bpm', '').strip())
                                except ValueError:
                                    pass
                            elif '/' in part:
                                try:
                                    bp_parts = part.replace('mmHg', '').split('/')
                                    systolic_bp = int(bp_parts[0].strip())
                                    diastolic_bp = int(bp_parts[1].strip())
                                except (ValueError, IndexError):
                                    pass

                        if weight is not None or heart_rate is not None or (systolic_bp is not None and diastolic_bp is not None):
                            VitalSign.objects.create(
                                date=date,
                                weight=weight,
                                heart_rate=heart_rate,
                                systolic_bp=systolic_bp,
                                diastolic_bp=diastolic_bp
                            )
                            imported_vitals += 1
                        else:
                            skipped_rows += 1

                    else:
                        skipped_rows += 1

                except Exception as e:
                    print(f"Error parsing row: {e}")
                    skipped_rows += 1

            flash_msg = f"Imported {imported_tests} blood tests and {imported_vitals} vital signs."
            if skipped_rows > 0:
                flash_msg += f" Skipped {skipped_rows} rows due to missing/invalid data."
            messages.success(request, flash_msg)

            return redirect('index')

        except Exception as e:
            print(f"File processing error: {e}")
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect('import_data')

    return render(request, 'import_data.html')

@login_required
def export_data(request):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Date', 'Type', 'Name', 'Value', 'Unit', 'Normal Min', 'Normal Max', 'Status', 'Notes'])

    tests = BloodTest.objects.all().order_by('-date')
    vitals = VitalSign.objects.all().order_by('-date')

    history_items = []

    for test in tests:
        history_items.append({
            'date': test.date,
            'type': 'Blood Test',
            'name': test.test_name,
            'value': test.value,
            'unit': test.unit,
            'normal_min': test.normal_min,
            'normal_max': test.normal_max,
            'status': 'Normal' if test.normal_min is not None and test.normal_max is not None and test.normal_min <= test.value <= test.normal_max else ('Out of Range' if test.normal_min is not None and test.normal_max is not None else 'N/A'),
            'notes': f"Range: {test.normal_min} - {test.normal_max}" if test.normal_min is not None and test.normal_max is not None else ""
        })

    for vital in vitals:
        bp_str = f"{vital.systolic_bp}/{vital.diastolic_bp}" if vital.systolic_bp is not None and vital.diastolic_bp is not None else ""
        hr_str = f"{vital.heart_rate} bpm" if vital.heart_rate is not None else ""
        weight_str = f"{vital.weight} kg" if vital.weight is not None else ""
        bbt_str = f"BBT: {vital.bbt}°C" if vital.bbt is not None else ""
        spo2_str = f"SpO2: {vital.spo2}%" if vital.spo2 is not None else ""
        rr_str = f"RR: {vital.respiratory_rate}/min" if vital.respiratory_rate is not None else ""

        details = [val for val in [weight_str, hr_str, bp_str, bbt_str, spo2_str, rr_str] if val]

        history_items.append({
            'date': vital.date,
            'type': 'Vitals',
            'name': 'Vital Signs',
            'value': ", ".join(details),
            'unit': '',
            'normal_min': '',
            'normal_max': '',
            'status': 'N/A',
            'notes': ''
        })

    history_items.sort(key=lambda x: x['date'], reverse=True)

    for item in history_items:
        writer.writerow([
            item['date'].strftime('%Y-%m-%d'),
            item['type'],
            item['name'],
            item['value'],
            item['unit'],
            item['normal_min'] if item['normal_min'] is not None else '',
            item['normal_max'] if item['normal_max'] is not None else '',
            item['status'],
            item['notes']
        ])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename=medical_history.csv'
    return response


# ===== Phase 2: Body Composition =====

@login_required
def body_composition_list(request):
    entries = BodyComposition.objects.all().order_by('-date')

    # Date range filtering
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        entries = entries.filter(date__gte=start_date)
    if end_date:
        entries = entries.filter(date__lte=end_date)

    # Summary statistics
    stats = entries.aggregate(
        avg_body_fat=Avg('body_fat_percentage'),
        avg_muscle_mass=Avg('skeletal_muscle_mass'),
        avg_whr=Avg('waist_to_hip_ratio'),
        total_entries=Count('id'),
    )

    # Chart data (last 30 entries, chronological)
    chart_entries = entries.order_by('date')[:30]
    chart_dates = [e.date.isoformat() for e in chart_entries]
    chart_body_fat = [e.body_fat_percentage for e in chart_entries if e.body_fat_percentage is not None]
    chart_muscle = [e.skeletal_muscle_mass for e in chart_entries if e.skeletal_muscle_mass is not None]

    # Pagination
    paginator = Paginator(entries, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'chart_dates': json.dumps(chart_dates),
        'chart_body_fat': json.dumps(chart_body_fat),
        'chart_muscle': json.dumps(chart_muscle),
    }
    return render(request, 'body_composition_list.html', context)

@login_required
def body_composition_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('body_composition_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            BodyComposition.objects.create(
                date=date,
                body_fat_percentage=float(request.POST.get('body_fat_percentage')) if request.POST.get('body_fat_percentage') else None,
                skeletal_muscle_mass=float(request.POST.get('skeletal_muscle_mass')) if request.POST.get('skeletal_muscle_mass') else None,
                bone_density=float(request.POST.get('bone_density')) if request.POST.get('bone_density') else None,
                waist_circumference=float(request.POST.get('waist_circumference')) if request.POST.get('waist_circumference') else None,
                hip_circumference=float(request.POST.get('hip_circumference')) if request.POST.get('hip_circumference') else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Body composition entry added!')
            return redirect('body_composition_list')
        except Exception:
            messages.error(request, 'Error adding body composition. Please try again.')
            return redirect('body_composition_add')
    return render(request, 'body_composition_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def body_composition_edit(request, pk):
    entry = get_object_or_404(BodyComposition, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.body_fat_percentage = float(request.POST.get('body_fat_percentage')) if request.POST.get('body_fat_percentage') else None
            entry.skeletal_muscle_mass = float(request.POST.get('skeletal_muscle_mass')) if request.POST.get('skeletal_muscle_mass') else None
            entry.bone_density = float(request.POST.get('bone_density')) if request.POST.get('bone_density') else None
            entry.waist_circumference = float(request.POST.get('waist_circumference')) if request.POST.get('waist_circumference') else None
            entry.hip_circumference = float(request.POST.get('hip_circumference')) if request.POST.get('hip_circumference') else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Body composition updated!')
            return redirect('body_composition_list')
        except Exception:
            messages.error(request, 'Error updating body composition.')
            return redirect('body_composition_edit', pk=pk)
    return render(request, 'body_composition_form.html', {'entry': entry, 'editing': True})

@login_required
def body_composition_delete(request, pk):
    if request.method == 'POST':
        entry = get_object_or_404(BodyComposition, id=pk)
        entry.delete()
        messages.success(request, 'Body composition entry deleted!')
    return redirect('body_composition_list')


# ===== Phase 2: Hydration Tracking =====

@login_required
def hydration_list(request):
    entries = HydrationLog.objects.all().order_by('-date')

    # Date range filtering
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        entries = entries.filter(date__gte=start_date)
    if end_date:
        entries = entries.filter(date__lte=end_date)

    # Summary statistics
    stats = entries.aggregate(
        avg_intake=Avg('fluid_intake_ml'),
        avg_goal=Avg('goal_ml'),
        total_entries=Count('id'),
    )
    # Calculate average goal achievement percentage
    all_entries_for_stats = list(entries)
    goal_percentages = [e.goal_percentage for e in all_entries_for_stats if e.goal_percentage is not None]
    stats['avg_goal_pct'] = round(sum(goal_percentages) / len(goal_percentages), 1) if goal_percentages else None
    stats['days_goal_met'] = sum(1 for p in goal_percentages if p >= 100)

    # Chart data (last 30 entries, chronological)
    chart_entries = entries.order_by('date')[:30]
    chart_dates = [e.date.isoformat() for e in chart_entries]
    chart_intake = [e.fluid_intake_ml for e in chart_entries]
    chart_goal = [e.goal_ml for e in chart_entries if e.goal_ml is not None]

    # Pagination
    paginator = Paginator(entries, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'chart_dates': json.dumps(chart_dates),
        'chart_intake': json.dumps(chart_intake),
        'chart_goal': json.dumps(chart_goal),
    }
    return render(request, 'hydration_list.html', context)

@login_required
def hydration_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('hydration_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            fluid_val = request.POST.get('fluid_intake_ml', '').strip()
            goal_val = request.POST.get('goal_ml', '').strip()
            HydrationLog.objects.create(
                date=date,
                fluid_intake_ml=float(fluid_val) if fluid_val else 0,
                goal_ml=float(goal_val) if goal_val else 2500,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Hydration log added!')
            return redirect('hydration_list')
        except Exception:
            messages.error(request, 'Error adding hydration log.')
            return redirect('hydration_add')
    return render(request, 'hydration_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def hydration_edit(request, pk):
    entry = get_object_or_404(HydrationLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            fluid_val = request.POST.get('fluid_intake_ml', '').strip()
            goal_val = request.POST.get('goal_ml', '').strip()
            entry.fluid_intake_ml = float(fluid_val) if fluid_val else 0
            entry.goal_ml = float(goal_val) if goal_val else 2500
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Hydration log updated!')
            return redirect('hydration_list')
        except Exception:
            messages.error(request, 'Error updating hydration log.')
            return redirect('hydration_edit', pk=pk)
    return render(request, 'hydration_form.html', {'entry': entry, 'editing': True})

@login_required
def hydration_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(HydrationLog, id=pk).delete()
        messages.success(request, 'Hydration log deleted!')
    return redirect('hydration_list')


# ===== Phase 2: Energy and Fatigue Scoring =====

@login_required
def energy_list(request):
    entries = EnergyFatigueLog.objects.all().order_by('-date')
    return render(request, 'energy_list.html', {'entries': entries})

@login_required
def energy_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('energy_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            EnergyFatigueLog.objects.create(
                date=date,
                energy_score=int(request.POST.get('energy_score', 5)),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Energy log added!')
            return redirect('energy_list')
        except Exception:
            messages.error(request, 'Error adding energy log.')
            return redirect('energy_add')
    return render(request, 'energy_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def energy_edit(request, pk):
    entry = get_object_or_404(EnergyFatigueLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.energy_score = int(request.POST.get('energy_score', 5))
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Energy log updated!')
            return redirect('energy_list')
        except Exception:
            messages.error(request, 'Error updating energy log.')
            return redirect('energy_edit', pk=pk)
    return render(request, 'energy_form.html', {'entry': entry, 'editing': True})

@login_required
def energy_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(EnergyFatigueLog, id=pk).delete()
        messages.success(request, 'Energy log deleted!')
    return redirect('energy_list')


# ===== Phase 2: Custom Vital Signs =====

@login_required
def custom_vitals_list(request):
    definitions = CustomVitalDefinition.objects.all()
    entries = CustomVitalEntry.objects.all().order_by('-date')
    return render(request, 'custom_vitals_list.html', {'definitions': definitions, 'entries': entries})

@login_required
def custom_vital_define(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        unit = request.POST.get('unit')
        if not name or not unit:
            messages.error(request, 'Name and unit are required.')
            return redirect('custom_vital_define')
        try:
            CustomVitalDefinition.objects.create(
                name=name,
                unit=unit,
                normal_min=float(request.POST.get('normal_min')) if request.POST.get('normal_min') else None,
                normal_max=float(request.POST.get('normal_max')) if request.POST.get('normal_max') else None,
                description=request.POST.get('description', ''),
            )
            messages.success(request, f'Custom vital "{name}" defined!')
            return redirect('custom_vitals_list')
        except Exception:
            messages.error(request, 'Error defining custom vital.')
            return redirect('custom_vital_define')
    return render(request, 'custom_vital_define.html')

@login_required
def custom_vital_add_entry(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        definition_id = request.POST.get('definition')
        if not date_str or not definition_id:
            messages.error(request, 'Date and metric type are required.')
            return redirect('custom_vital_add_entry')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            definition = get_object_or_404(CustomVitalDefinition, id=definition_id)
            CustomVitalEntry.objects.create(
                definition=definition,
                date=date,
                value=float(request.POST.get('value', 0)),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Custom vital entry added!')
            return redirect('custom_vitals_list')
        except Exception:
            messages.error(request, 'Error adding custom vital entry.')
            return redirect('custom_vital_add_entry')
    definitions = CustomVitalDefinition.objects.all()
    return render(request, 'custom_vital_entry_form.html', {
        'definitions': definitions,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'editing': False,
    })

@login_required
def custom_vital_edit_entry(request, pk):
    entry = get_object_or_404(CustomVitalEntry, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            definition_id = request.POST.get('definition')
            if definition_id:
                entry.definition = get_object_or_404(CustomVitalDefinition, id=definition_id)
            entry.value = float(request.POST.get('value', 0))
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Custom vital entry updated!')
            return redirect('custom_vitals_list')
        except Exception:
            messages.error(request, 'Error updating custom vital entry.')
            return redirect('custom_vital_edit_entry', pk=pk)
    definitions = CustomVitalDefinition.objects.all()
    return render(request, 'custom_vital_entry_form.html', {
        'entry': entry,
        'definitions': definitions,
        'editing': True,
    })

@login_required
def custom_vital_delete_entry(request, pk):
    if request.method == 'POST':
        get_object_or_404(CustomVitalEntry, id=pk).delete()
        messages.success(request, 'Custom vital entry deleted!')
    return redirect('custom_vitals_list')


# ===== Phase 2: Anatomical Pain Mapping =====


def _safe_redirect(request, default='index'):
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect(default)


@login_required
def add_annotation(request, model_type, object_id):
    if request.method == 'POST':
        note = request.POST.get('note', '').strip()
        if not note:
            messages.error(request, 'Please enter a note.')
        elif model_type == 'blood_test':
            obj = get_object_or_404(BloodTest, id=object_id)
            DataPointAnnotation.objects.create(blood_test=obj, note=note)
            messages.success(request, 'Annotation added successfully!')
        elif model_type == 'vital_sign':
            obj = get_object_or_404(VitalSign, id=object_id)
            DataPointAnnotation.objects.create(vital_sign=obj, note=note)
            messages.success(request, 'Annotation added successfully!')
        else:
            messages.error(request, 'Invalid data type.')

    return _safe_redirect(request)


@login_required
def delete_annotation(request, annotation_id):
    if request.method == 'POST':
        annotation = get_object_or_404(DataPointAnnotation, id=annotation_id)
        annotation.delete()
        messages.success(request, 'Annotation deleted successfully!')
    return _safe_redirect(request)


# --- Bulk Data Editing Interface ---

@login_required
def bulk_edit(request):
    if request.method == 'POST':
        updated = 0
        deleted_ids = request.POST.getlist('delete_ids')

        if deleted_ids:
            BloodTest.objects.filter(id__in=deleted_ids).delete()

        test_ids = request.POST.getlist('test_ids')
        remaining_ids = [tid for tid in test_ids if tid not in deleted_ids]

        if remaining_ids:
            tests_map = {str(t.id): t for t in BloodTest.objects.filter(id__in=remaining_ids)}
            to_update = []
            for test_id in remaining_ids:
                test = tests_map.get(test_id)
                if not test:
                    continue
                try:
                    new_value = request.POST.get(f'value_{test_id}')
                    new_date = request.POST.get(f'date_{test_id}')
                    if new_value is not None and new_date:
                        test.value = float(new_value)
                        test.date = datetime.strptime(new_date, '%Y-%m-%d').date()
                        to_update.append(test)
                        updated += 1
                except (ValueError, TypeError):
                    continue
            if to_update:
                BloodTest.objects.bulk_update(to_update, ['value', 'date'])

        deleted_count = len(deleted_ids)
        parts = []
        if updated:
            parts.append(f'{updated} record(s) updated')
        if deleted_count:
            parts.append(f'{deleted_count} record(s) deleted')
        if parts:
            messages.success(request, '. '.join(parts) + '.')
        return redirect('bulk_edit')

    tests = BloodTest.objects.all().order_by('-date', 'test_name')
    return render(request, 'bulk_edit.html', {'tests': tests})


# --- Customizable Dashboard helpers and views ---

DEFAULT_WIDGETS = [
    ('summary_cards', 0),
    ('recent_results', 1),
    ('vital_signs', 2),
    ('blood_charts', 3),
    ('vitals_charts', 4),
    ('comparative_bars', 5),
    ('boxplots', 6),
]

def _get_dashboard_widgets():
    widgets = list(DashboardWidget.objects.all())
    if not widgets:
        for wtype, pos in DEFAULT_WIDGETS:
            DashboardWidget.objects.create(widget_type=wtype, position=pos, visible=True)
        widgets = list(DashboardWidget.objects.all())
    return widgets


@login_required
def customize_dashboard(request):
    widgets = _get_dashboard_widgets()
    return render(request, 'customize_dashboard.html', {'widgets': widgets})


@login_required
def update_widgets(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for item in data.get('widgets', []):
                widget_id = item.get('id')
                position = item.get('position')
                visible = item.get('visible')
                if widget_id is not None:
                    try:
                        w = DashboardWidget.objects.get(id=int(widget_id))
                        if position is not None:
                            w.position = int(position)
                        if visible is not None:
                            w.visible = bool(visible)
                        w.save()
                    except DashboardWidget.DoesNotExist:
                        pass
            return JsonResponse({'status': 'ok'})
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


@login_required
def global_search(request):
    """Phase 3: Global search API endpoint for finding tests, vitals, and journal entries."""
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'results': []})

    results = []

    # Search Blood Tests
    blood_tests = BloodTest.objects.filter(
        models_Q(test_name__icontains=q) | models_Q(category__icontains=q)
    ).order_by('-date')[:10]
    for t in blood_tests:
        results.append({
            'type': 'blood_test',
            'icon': 'fa-vial',
            'name': t.test_name,
            'value': f"{t.value} {t.unit}",
            'date': t.date.isoformat(),
            'url': reverse('chart', args=[t.test_name]),
        })

    # Search Vital Signs by date
    try:
        from datetime import date as date_cls
        if re.match(r'^\d{4}-\d{2}-\d{2}$', q):
            search_date = date_cls.fromisoformat(q)
            vitals = VitalSign.objects.filter(date=search_date)[:5]
            for v in vitals:
                results.append({
                    'type': 'vital_sign',
                    'icon': 'fa-heartbeat',
                    'name': f"Vitals on {v.date}",
                    'value': f"HR: {v.heart_rate or 'N/A'}, BP: {v.systolic_bp or 'N/A'}/{v.diastolic_bp or 'N/A'}",
                    'date': v.date.isoformat(),
                    'url': reverse('vitals'),
                })
    except (ValueError, TypeError):
        pass

    # Search Symptom Journal
    symptoms = SymptomJournal.objects.filter(
        models_Q(symptom__icontains=q) | models_Q(notes__icontains=q)
    ).order_by('-date')[:5]
    for s in symptoms:
        results.append({
            'type': 'symptom',
            'icon': 'fa-notes-medical',
            'name': f"Symptom: {s.symptom[:50]}",
            'value': f"Severity: {s.severity}/5" if s.severity else '',
            'date': s.date.isoformat(),
            'url': reverse('symptom_list'),
        })

    # Search Annotations
    annotations = DataPointAnnotation.objects.filter(
        note__icontains=q
    ).order_by('-created_at')[:5]
    for a in annotations:
        results.append({
            'type': 'annotation',
            'icon': 'fa-sticky-note',
            'name': f"Note: {a.note[:50]}",
            'value': '',
            'date': a.created_at.isoformat() if a.created_at else '',
            'url': reverse('index'),
        })

    return JsonResponse({'results': results})


# ===== Phase 5: Wearable Integrations =====

def wearable_device_list(request):
    entries = WearableDevice.objects.all().order_by('-created_at')
    from tracker.integrations.registry import is_oauth_platform, get_client
    client_cache = {}
    for entry in entries:
        entry.supports_oauth = is_oauth_platform(entry.platform)
        entry.has_token = bool(entry.access_token)
        if entry.platform not in client_cache:
            client_cache[entry.platform] = get_client(entry.platform)
        client = client_cache[entry.platform]
        if client:
            config = client.get_oauth_config()
            entry.is_configured = bool(config.client_id and config.client_secret)
        else:
            entry.is_configured = False
    return render(request, 'wearable_device_list.html', {'entries': entries})

def wearable_device_add(request):
    if request.method == 'POST':
        try:
            WearableDevice.objects.create(
                user=request.user if request.user.is_authenticated else None,
                platform=request.POST.get('platform', ''),
                device_name=request.POST.get('device_name', ''),
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'Wearable device added!')
            return redirect('wearable_device_list')
        except Exception:
            messages.error(request, 'Error adding wearable device.')
            return redirect('wearable_device_add')
    return render(request, 'wearable_device_form.html', {'editing': False, 'platforms': WEARABLE_PLATFORMS})

def wearable_device_edit(request, pk):
    entry = get_object_or_404(WearableDevice, id=pk)
    if request.method == 'POST':
        try:
            entry.platform = request.POST.get('platform', '')
            entry.device_name = request.POST.get('device_name', '')
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.save()
            messages.success(request, 'Wearable device updated!')
            return redirect('wearable_device_list')
        except Exception:
            messages.error(request, 'Error updating wearable device.')
            return redirect('wearable_device_edit', pk=pk)
    return render(request, 'wearable_device_form.html', {'entry': entry, 'editing': True, 'platforms': WEARABLE_PLATFORMS})

def wearable_device_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(WearableDevice, id=pk).delete()
        messages.success(request, 'Wearable device deleted!')
    return redirect('wearable_device_list')

def wearable_device_sync(request, pk):
    device = get_object_or_404(WearableDevice, id=pk)
    if request.method == 'POST':
        sync_log = device.trigger_sync()
        if sync_log.status == 'success':
            messages.success(request, f'Sync completed! {sync_log.records_synced} records synced from {device.get_platform_display()}.')
        else:
            messages.error(request, f'Sync failed: {sync_log.error_message}')
    return redirect('wearable_device_list')

def sync_log_list(request):
    entries = WearableSyncLog.objects.all().order_by('-started_at')
    return render(request, 'sync_log_list.html', {'entries': entries})


@login_required
def wearable_connect(request, pk):
    """Initiate OAuth connection for a wearable device."""
    import secrets
    device = get_object_or_404(WearableDevice, id=pk)
    from tracker.integrations.registry import get_client, is_oauth_platform
    if not is_oauth_platform(device.platform):
        messages.error(request, f'{device.get_platform_display()} does not support OAuth connection.')
        return redirect('wearable_device_list')

    client = get_client(device.platform)
    if not client:
        messages.error(request, f'No integration client for {device.get_platform_display()}.')
        return redirect('wearable_device_list')

    config = client.get_oauth_config()
    if not config.client_id or not config.client_secret:
        messages.error(request, f'{device.get_platform_display()} OAuth credentials are not configured.')
        return redirect('wearable_device_list')

    callback_url = request.build_absolute_uri(
        reverse('wearable_oauth_callback', kwargs={'platform': device.platform})
    )
    state = secrets.token_urlsafe(32)
    request.session[f'oauth_state_{device.platform}'] = state
    request.session[f'oauth_device_id_{device.platform}'] = device.pk

    auth_url = client.get_authorization_url(callback_url, state=state)
    # For Garmin OAuth 1.0a, store request tokens in session for the callback
    if hasattr(client, '_request_token'):
        request.session[f'oauth_request_token_{device.platform}'] = client._request_token
        request.session[f'oauth_request_token_secret_{device.platform}'] = client._request_token_secret
    return redirect(auth_url)


@login_required
def wearable_oauth_callback(request, platform):
    """Handle OAuth callback from a wearable platform."""
    from tracker.integrations.registry import get_client
    code = request.GET.get('code') or request.GET.get('oauth_verifier', '')
    state = request.GET.get('state', '')
    stored_state = request.session.pop(f'oauth_state_{platform}', '')
    device_id = request.session.pop(f'oauth_device_id_{platform}', None)

    if not code:
        messages.error(request, 'Authorization failed: no code received.')
        return redirect('wearable_device_list')

    # Validate state for OAuth2 platforms (not applicable for OAuth 1.0a like Garmin)
    if stored_state and state and state != stored_state:
        messages.error(request, 'Authorization failed: state mismatch.')
        return redirect('wearable_device_list')

    if not device_id:
        messages.error(request, 'Authorization failed: no device found in session.')
        return redirect('wearable_device_list')

    device = get_object_or_404(WearableDevice, id=device_id)
    client = get_client(platform)
    if not client:
        messages.error(request, f'No integration client for this platform.')
        return redirect('wearable_device_list')

    try:
        callback_url = request.build_absolute_uri(
            reverse('wearable_oauth_callback', kwargs={'platform': platform})
        )
        # For Garmin OAuth 1.0a, pass request tokens from session
        extra_kwargs = {}
        request_token = request.session.pop(f'oauth_request_token_{platform}', '')
        request_token_secret = request.session.pop(f'oauth_request_token_secret_{platform}', '')
        if request_token and request_token_secret:
            extra_kwargs['request_token'] = request_token
            extra_kwargs['request_token_secret'] = request_token_secret
        token_data = client.exchange_code_for_token(code, callback_url, **extra_kwargs)
        client.update_device_tokens(device, token_data)
        if token_data.get('scope'):
            device.scope = token_data['scope'] if isinstance(token_data['scope'], str) else ' '.join(token_data['scope'])
            device.save(update_fields=['scope'])
        messages.success(request, f'{device.get_platform_display()} connected successfully!')
    except Exception as exc:
        messages.error(request, f'Failed to connect {device.get_platform_display()}: {exc}')

    return redirect('wearable_device_list')


@login_required
def wearable_disconnect(request, pk):
    """Disconnect (revoke tokens) for a wearable device."""
    if request.method == 'POST':
        device = get_object_or_404(WearableDevice, id=pk)
        device.access_token = ''
        device.refresh_token = ''
        device.token_expires_at = None
        device.scope = ''
        device.save(update_fields=['access_token', 'refresh_token', 'token_expires_at', 'scope'])
        messages.success(request, f'{device.get_platform_display()} disconnected.')
    return redirect('wearable_device_list')


@login_required
def wearable_sync(request, pk):
    """Trigger a data sync for a wearable device."""
    if request.method == 'POST':
        device = get_object_or_404(WearableDevice, id=pk)
        if not device.access_token:
            messages.error(request, f'{device.get_platform_display()} is not connected. Please connect first.')
            return redirect('wearable_device_list')

        from tracker.integrations.registry import get_client
        client = get_client(device.platform)
        if not client:
            messages.error(request, f'No integration client for {device.get_platform_display()}.')
            return redirect('wearable_device_list')

        sync_log = client.sync_data(device)
        if sync_log.status == 'success':
            messages.success(request, f'Synced {sync_log.records_synced} records from {device.get_platform_display()}.')
        else:
            messages.error(request, f'Sync failed: {sync_log.error_message}')
    return redirect('wearable_device_list')


# ===== Phase 6: Sleep & Circadian =====

@login_required
def sleep_list(request):
    entries = SleepLog.objects.all().order_by('-date')

    # Date range filtering
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        entries = entries.filter(date__gte=start_date)
    if end_date:
        entries = entries.filter(date__lte=end_date)

    # Summary statistics
    stats = entries.aggregate(
        avg_total_sleep=Avg('total_sleep_minutes'),
        avg_quality=Avg('sleep_quality_score'),
        avg_rem=Avg('rem_minutes'),
        avg_deep=Avg('deep_sleep_minutes'),
        total_entries=Count('id'),
    )

    # Chart data (last 30 entries, chronological)
    chart_entries = entries.order_by('date')[:30]
    chart_dates = [e.date.isoformat() for e in chart_entries]
    chart_quality = [e.sleep_quality_score for e in chart_entries if e.sleep_quality_score is not None]
    chart_total = [e.total_sleep_minutes for e in chart_entries if e.total_sleep_minutes is not None]

    # Pagination
    paginator = Paginator(entries, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'chart_dates': json.dumps(chart_dates),
        'chart_quality': json.dumps(chart_quality),
        'chart_total': json.dumps(chart_total),
    }
    return render(request, 'sleep_list.html', context)

@login_required
def sleep_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('sleep_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            total = request.POST.get('total_sleep_minutes', '').strip()
            rem = request.POST.get('rem_minutes', '').strip()
            deep = request.POST.get('deep_sleep_minutes', '').strip()
            light = request.POST.get('light_sleep_minutes', '').strip()
            awake = request.POST.get('awake_minutes', '').strip()
            quality = request.POST.get('sleep_quality_score', '').strip()
            bedtime_val = request.POST.get('bedtime', '').strip() or None
            wake_val = request.POST.get('wake_time', '').strip() or None
            SleepLog.objects.create(
                date=date,
                bedtime=bedtime_val,
                wake_time=wake_val,
                total_sleep_minutes=int(total) if total else None,
                rem_minutes=int(rem) if rem else None,
                deep_sleep_minutes=int(deep) if deep else None,
                light_sleep_minutes=int(light) if light else None,
                awake_minutes=int(awake) if awake else None,
                sleep_quality_score=int(quality) if quality else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Sleep log added!')
            return redirect('sleep_list')
        except Exception:
            messages.error(request, 'Error adding sleep log.')
            return redirect('sleep_add')
    return render(request, 'sleep_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def sleep_edit(request, pk):
    entry = get_object_or_404(SleepLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.bedtime = request.POST.get('bedtime', '').strip() or None
            entry.wake_time = request.POST.get('wake_time', '').strip() or None
            total = request.POST.get('total_sleep_minutes', '').strip()
            rem = request.POST.get('rem_minutes', '').strip()
            deep = request.POST.get('deep_sleep_minutes', '').strip()
            light = request.POST.get('light_sleep_minutes', '').strip()
            awake = request.POST.get('awake_minutes', '').strip()
            quality = request.POST.get('sleep_quality_score', '').strip()
            entry.total_sleep_minutes = int(total) if total else None
            entry.rem_minutes = int(rem) if rem else None
            entry.deep_sleep_minutes = int(deep) if deep else None
            entry.light_sleep_minutes = int(light) if light else None
            entry.awake_minutes = int(awake) if awake else None
            entry.sleep_quality_score = int(quality) if quality else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Sleep log updated!')
            return redirect('sleep_list')
        except Exception:
            messages.error(request, 'Error updating sleep log.')
            return redirect('sleep_edit', pk=pk)
    return render(request, 'sleep_form.html', {'entry': entry, 'editing': True})

@login_required
def sleep_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(SleepLog, id=pk).delete()
        messages.success(request, 'Sleep log deleted!')
    return redirect('sleep_list')


# ===== Phase 6: Circadian Rhythm =====

@login_required
def circadian_list(request):
    entries = CircadianRhythmLog.objects.all().order_by('-date')
    return render(request, 'circadian_list.html', {'entries': entries})

@login_required
def circadian_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('circadian_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            light_exp = request.POST.get('light_exposure_minutes', '').strip()
            CircadianRhythmLog.objects.create(
                date=date,
                wake_time=request.POST.get('wake_time', '').strip() or None,
                sleep_onset=request.POST.get('sleep_onset', '').strip() or None,
                peak_energy_time=request.POST.get('peak_energy_time', '').strip() or None,
                lowest_energy_time=request.POST.get('lowest_energy_time', '').strip() or None,
                light_exposure_minutes=int(light_exp) if light_exp else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Circadian rhythm log added!')
            return redirect('circadian_list')
        except Exception:
            messages.error(request, 'Error adding circadian rhythm log.')
            return redirect('circadian_add')
    return render(request, 'circadian_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def circadian_edit(request, pk):
    entry = get_object_or_404(CircadianRhythmLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.wake_time = request.POST.get('wake_time', '').strip() or None
            entry.sleep_onset = request.POST.get('sleep_onset', '').strip() or None
            entry.peak_energy_time = request.POST.get('peak_energy_time', '').strip() or None
            entry.lowest_energy_time = request.POST.get('lowest_energy_time', '').strip() or None
            light_exp = request.POST.get('light_exposure_minutes', '').strip()
            entry.light_exposure_minutes = int(light_exp) if light_exp else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Circadian rhythm log updated!')
            return redirect('circadian_list')
        except Exception:
            messages.error(request, 'Error updating circadian rhythm log.')
            return redirect('circadian_edit', pk=pk)
    return render(request, 'circadian_form.html', {'entry': entry, 'editing': True})

@login_required
def circadian_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(CircadianRhythmLog, id=pk).delete()
        messages.success(request, 'Circadian rhythm log deleted!')
    return redirect('circadian_list')


# ===== Phase 6: Dream Journal =====

@login_required
def dream_list(request):
    entries = DreamJournal.objects.all().order_by('-date')
    return render(request, 'dream_list.html', {'entries': entries})

@login_required
def dream_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('dream_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            lucidity = request.POST.get('lucidity_level', '').strip()
            DreamJournal.objects.create(
                date=date,
                dream_description=request.POST.get('dream_description', ''),
                lucidity_level=int(lucidity) if lucidity else None,
                mood_on_waking=request.POST.get('mood_on_waking', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Dream journal entry added!')
            return redirect('dream_list')
        except Exception:
            messages.error(request, 'Error adding dream journal entry.')
            return redirect('dream_add')
    return render(request, 'dream_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def dream_edit(request, pk):
    entry = get_object_or_404(DreamJournal, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.dream_description = request.POST.get('dream_description', '')
            lucidity = request.POST.get('lucidity_level', '').strip()
            entry.lucidity_level = int(lucidity) if lucidity else None
            entry.mood_on_waking = request.POST.get('mood_on_waking', '')
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Dream journal entry updated!')
            return redirect('dream_list')
        except Exception:
            messages.error(request, 'Error updating dream journal entry.')
            return redirect('dream_edit', pk=pk)
    return render(request, 'dream_form.html', {'entry': entry, 'editing': True})

@login_required
def dream_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(DreamJournal, id=pk).delete()
        messages.success(request, 'Dream journal entry deleted!')
    return redirect('dream_list')


# ===== Phase 6: Macronutrient Log =====

@login_required
def macro_list(request):
    entries = MacronutrientLog.objects.all().order_by('-date')

    # Date range filtering
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        entries = entries.filter(date__gte=start_date)
    if end_date:
        entries = entries.filter(date__lte=end_date)

    # Summary statistics
    stats = entries.aggregate(
        avg_protein=Avg('protein_grams'),
        avg_carbs=Avg('carbohydrate_grams'),
        avg_fat=Avg('fat_grams'),
        avg_calories=Avg('calories'),
        avg_fiber=Avg('fiber_grams'),
        total_entries=Count('id'),
    )

    # Chart data (last 30 entries, chronological)
    chart_entries = entries.order_by('date')[:30]
    chart_dates = [e.date.isoformat() for e in chart_entries]
    chart_protein = [e.protein_grams for e in chart_entries if e.protein_grams is not None]
    chart_carbs = [e.carbohydrate_grams for e in chart_entries if e.carbohydrate_grams is not None]
    chart_fat = [e.fat_grams for e in chart_entries if e.fat_grams is not None]
    chart_calories = [e.calories for e in chart_entries if e.calories is not None]

    # Pagination
    paginator = Paginator(entries, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'chart_dates': json.dumps(chart_dates),
        'chart_protein': json.dumps(chart_protein),
        'chart_carbs': json.dumps(chart_carbs),
        'chart_fat': json.dumps(chart_fat),
        'chart_calories': json.dumps(chart_calories),
    }
    return render(request, 'macro_list.html', context)

@login_required
def macro_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('macro_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            protein = request.POST.get('protein_grams', '').strip()
            carbs = request.POST.get('carbohydrate_grams', '').strip()
            fat = request.POST.get('fat_grams', '').strip()
            calories = request.POST.get('calories', '').strip()
            fiber = request.POST.get('fiber_grams', '').strip()
            MacronutrientLog.objects.create(
                date=date,
                protein_grams=float(protein) if protein else None,
                carbohydrate_grams=float(carbs) if carbs else None,
                fat_grams=float(fat) if fat else None,
                calories=float(calories) if calories else None,
                fiber_grams=float(fiber) if fiber else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Macronutrient log added!')
            return redirect('macro_list')
        except Exception:
            messages.error(request, 'Error adding macronutrient log.')
            return redirect('macro_add')
    return render(request, 'macro_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def macro_edit(request, pk):
    entry = get_object_or_404(MacronutrientLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            protein = request.POST.get('protein_grams', '').strip()
            carbs = request.POST.get('carbohydrate_grams', '').strip()
            fat = request.POST.get('fat_grams', '').strip()
            calories = request.POST.get('calories', '').strip()
            fiber = request.POST.get('fiber_grams', '').strip()
            entry.protein_grams = float(protein) if protein else None
            entry.carbohydrate_grams = float(carbs) if carbs else None
            entry.fat_grams = float(fat) if fat else None
            entry.calories = float(calories) if calories else None
            entry.fiber_grams = float(fiber) if fiber else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Macronutrient log updated!')
            return redirect('macro_list')
        except Exception:
            messages.error(request, 'Error updating macronutrient log.')
            return redirect('macro_edit', pk=pk)
    return render(request, 'macro_form.html', {'entry': entry, 'editing': True})

@login_required
def macro_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(MacronutrientLog, id=pk).delete()
        messages.success(request, 'Macronutrient log deleted!')
    return redirect('macro_list')


# ===== Phase 6: Micronutrient Log =====

@login_required
def micro_list(request):
    entries = MicronutrientLog.objects.all().order_by('-date')
    return render(request, 'micro_list.html', {'entries': entries})

@login_required
def micro_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('micro_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            amount = request.POST.get('amount', '').strip()
            MicronutrientLog.objects.create(
                date=date,
                nutrient_name=request.POST.get('nutrient_name', ''),
                amount=float(amount) if amount else None,
                unit=request.POST.get('unit', ''),
                deficiency_risk=request.POST.get('deficiency_risk', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Micronutrient log added!')
            return redirect('micro_list')
        except Exception:
            messages.error(request, 'Error adding micronutrient log.')
            return redirect('micro_add')
    return render(request, 'micro_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def micro_edit(request, pk):
    entry = get_object_or_404(MicronutrientLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.nutrient_name = request.POST.get('nutrient_name', '')
            amount = request.POST.get('amount', '').strip()
            entry.amount = float(amount) if amount else None
            entry.unit = request.POST.get('unit', '')
            entry.deficiency_risk = request.POST.get('deficiency_risk', '')
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Micronutrient log updated!')
            return redirect('micro_list')
        except Exception:
            messages.error(request, 'Error updating micronutrient log.')
            return redirect('micro_edit', pk=pk)
    return render(request, 'micro_form.html', {'entry': entry, 'editing': True})

@login_required
def micro_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(MicronutrientLog, id=pk).delete()
        messages.success(request, 'Micronutrient log deleted!')
    return redirect('micro_list')


# ===== Phase 6: Food Entry =====

@login_required
def food_list(request):
    entries = FoodEntry.objects.all().order_by('-date')
    return render(request, 'food_list.html', {'entries': entries})

@login_required
def food_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('food_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            calories = request.POST.get('calories', '').strip()
            protein = request.POST.get('protein_grams', '').strip()
            carbs = request.POST.get('carbohydrate_grams', '').strip()
            fat = request.POST.get('fat_grams', '').strip()
            FoodEntry.objects.create(
                date=date,
                food_name=request.POST.get('food_name', ''),
                barcode=request.POST.get('barcode', ''),
                serving_size=request.POST.get('serving_size', ''),
                calories=float(calories) if calories else None,
                protein_grams=float(protein) if protein else None,
                carbohydrate_grams=float(carbs) if carbs else None,
                fat_grams=float(fat) if fat else None,
                source=request.POST.get('source', ''),
                food_database_id=request.POST.get('food_database_id', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Food entry added!')
            return redirect('food_list')
        except Exception:
            messages.error(request, 'Error adding food entry.')
            return redirect('food_add')
    return render(request, 'food_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def food_edit(request, pk):
    entry = get_object_or_404(FoodEntry, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.food_name = request.POST.get('food_name', '')
            entry.barcode = request.POST.get('barcode', '')
            entry.serving_size = request.POST.get('serving_size', '')
            calories = request.POST.get('calories', '').strip()
            protein = request.POST.get('protein_grams', '').strip()
            carbs = request.POST.get('carbohydrate_grams', '').strip()
            fat = request.POST.get('fat_grams', '').strip()
            entry.calories = float(calories) if calories else None
            entry.protein_grams = float(protein) if protein else None
            entry.carbohydrate_grams = float(carbs) if carbs else None
            entry.fat_grams = float(fat) if fat else None
            entry.source = request.POST.get('source', '')
            entry.food_database_id = request.POST.get('food_database_id', '')
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Food entry updated!')
            return redirect('food_list')
        except Exception:
            messages.error(request, 'Error updating food entry.')
            return redirect('food_edit', pk=pk)
    return render(request, 'food_form.html', {'entry': entry, 'editing': True})

@login_required
def food_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(FoodEntry, id=pk).delete()
        messages.success(request, 'Food entry deleted!')
    return redirect('food_list')


# ===== Phase 6: Fasting Log =====

@login_required
def fasting_list(request):
    entries = FastingLog.objects.all().order_by('-date')
    return render(request, 'fasting_list.html', {'entries': entries})

@login_required
def fasting_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('fasting_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            target = request.POST.get('target_hours', '').strip()
            actual = request.POST.get('actual_hours', '').strip()
            FastingLog.objects.create(
                date=date,
                fast_start=request.POST.get('fast_start', '').strip() or None,
                fast_end=request.POST.get('fast_end', '').strip() or None,
                target_hours=float(target) if target else None,
                actual_hours=float(actual) if actual else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Fasting log added!')
            return redirect('fasting_list')
        except Exception:
            messages.error(request, 'Error adding fasting log.')
            return redirect('fasting_add')
    return render(request, 'fasting_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def fasting_edit(request, pk):
    entry = get_object_or_404(FastingLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.fast_start = request.POST.get('fast_start', '').strip() or None
            entry.fast_end = request.POST.get('fast_end', '').strip() or None
            target = request.POST.get('target_hours', '').strip()
            actual = request.POST.get('actual_hours', '').strip()
            entry.target_hours = float(target) if target else None
            entry.actual_hours = float(actual) if actual else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Fasting log updated!')
            return redirect('fasting_list')
        except Exception:
            messages.error(request, 'Error updating fasting log.')
            return redirect('fasting_edit', pk=pk)
    return render(request, 'fasting_form.html', {'entry': entry, 'editing': True})

@login_required
def fasting_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(FastingLog, id=pk).delete()
        messages.success(request, 'Fasting log deleted!')
    return redirect('fasting_list')


# ===== Phase 6: Caffeine & Alcohol Log =====

@login_required
def caffeine_alcohol_list(request):
    entries = CaffeineAlcoholLog.objects.all().order_by('-date')
    return render(request, 'caffeine_alcohol_list.html', {'entries': entries})

@login_required
def caffeine_alcohol_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('caffeine_alcohol_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            amount = request.POST.get('amount_mg', '').strip()
            CaffeineAlcoholLog.objects.create(
                date=date,
                substance=request.POST.get('substance', ''),
                amount_mg=float(amount) if amount else None,
                drink_name=request.POST.get('drink_name', ''),
                time_consumed=request.POST.get('time_consumed', '').strip() or None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Caffeine/alcohol log added!')
            return redirect('caffeine_alcohol_list')
        except Exception:
            messages.error(request, 'Error adding caffeine/alcohol log.')
            return redirect('caffeine_alcohol_add')
    return render(request, 'caffeine_alcohol_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def caffeine_alcohol_edit(request, pk):
    entry = get_object_or_404(CaffeineAlcoholLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.substance = request.POST.get('substance', '')
            amount = request.POST.get('amount_mg', '').strip()
            entry.amount_mg = float(amount) if amount else None
            entry.drink_name = request.POST.get('drink_name', '')
            entry.time_consumed = request.POST.get('time_consumed', '').strip() or None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Caffeine/alcohol log updated!')
            return redirect('caffeine_alcohol_list')
        except Exception:
            messages.error(request, 'Error updating caffeine/alcohol log.')
            return redirect('caffeine_alcohol_edit', pk=pk)
    return render(request, 'caffeine_alcohol_form.html', {'entry': entry, 'editing': True})

@login_required
def caffeine_alcohol_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(CaffeineAlcoholLog, id=pk).delete()
        messages.success(request, 'Caffeine/alcohol log deleted!')
    return redirect('caffeine_alcohol_list')


# ===== Phase 7: User Profile =====

def user_profile_list(request):
    entries = UserProfile.objects.select_related('user').all().order_by('-created_at')
    return render(request, 'user_profile_list.html', {'entries': entries})

def user_profile_add(request):
    if request.method == 'POST':
        try:
            username = request.POST.get('username', '')
            user = User.objects.create_user(username=username)
            user.set_unusable_password()
            user.save()
            UserProfile.objects.create(
                user=user,
                role=request.POST.get('role', 'user'),
            )
            messages.success(request, 'User profile added!')
            return redirect('user_profile_list')
        except Exception:
            messages.error(request, 'Error adding user profile.')
            return redirect('user_profile_add')
    return render(request, 'user_profile_form.html', {'editing': False})

def user_profile_edit(request, pk):
    entry = get_object_or_404(UserProfile, id=pk)
    if request.method == 'POST':
        try:
            entry.user.username = request.POST.get('username', '')
            entry.user.is_active = request.POST.get('is_active') == 'on'
            entry.user.save()
            entry.role = request.POST.get('role', '')
            entry.save()
            messages.success(request, 'User profile updated!')
            return redirect('user_profile_list')
        except Exception:
            messages.error(request, 'Error updating user profile.')
            return redirect('user_profile_edit', pk=pk)
    return render(request, 'user_profile_form.html', {'entry': entry, 'editing': True})

def user_profile_delete(request, pk):
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, id=pk)
        profile.user.delete()
        messages.success(request, 'User profile deleted!')
    return redirect('user_profile_list')


# ===== Phase 7: Family Account =====

def family_account_list(request):
    entries = FamilyAccount.objects.all().order_by('-created_at')
    return render(request, 'family_account_list.html', {'entries': entries})

def family_account_add(request):
    if request.method == 'POST':
        try:
            FamilyAccount.objects.create(
                primary_user=request.POST.get('primary_user', ''),
                member_name=request.POST.get('member_name', ''),
                relationship=request.POST.get('relationship', ''),
                is_minor=request.POST.get('is_minor') == 'on',
            )
            messages.success(request, 'Family account added!')
            return redirect('family_account_list')
        except Exception:
            messages.error(request, 'Error adding family account.')
            return redirect('family_account_add')
    return render(request, 'family_account_form.html', {'editing': False})

def family_account_edit(request, pk):
    entry = get_object_or_404(FamilyAccount, id=pk)
    if request.method == 'POST':
        try:
            entry.primary_user = request.POST.get('primary_user', '')
            entry.member_name = request.POST.get('member_name', '')
            entry.relationship = request.POST.get('relationship', '')
            entry.is_minor = request.POST.get('is_minor') == 'on'
            entry.save()
            messages.success(request, 'Family account updated!')
            return redirect('family_account_list')
        except Exception:
            messages.error(request, 'Error updating family account.')
            return redirect('family_account_edit', pk=pk)
    return render(request, 'family_account_form.html', {'entry': entry, 'editing': True})

def family_account_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(FamilyAccount, id=pk).delete()
        messages.success(request, 'Family account deleted!')
    return redirect('family_account_list')


# ===== Phase 7: Consent Log =====

def consent_log_list(request):
    entries = ConsentLog.objects.all().order_by('-accepted_at')
    return render(request, 'consent_log_list.html', {'entries': entries})

def consent_log_add(request):
    if request.method == 'POST':
        try:
            ConsentLog.objects.create(
                consent_type=request.POST.get('consent_type', ''),
                version=request.POST.get('version', ''),
                accepted=request.POST.get('accepted') == 'on',
                ip_address=request.POST.get('ip_address', ''),
            )
            messages.success(request, 'Consent log added!')
            return redirect('consent_log_list')
        except Exception:
            messages.error(request, 'Error adding consent log.')
            return redirect('consent_log_add')
    return render(request, 'consent_log_form.html', {'editing': False})

def consent_log_edit(request, pk):
    entry = get_object_or_404(ConsentLog, id=pk)
    if request.method == 'POST':
        try:
            entry.consent_type = request.POST.get('consent_type', '')
            entry.version = request.POST.get('version', '')
            entry.accepted = request.POST.get('accepted') == 'on'
            entry.ip_address = request.POST.get('ip_address', '')
            entry.save()
            messages.success(request, 'Consent log updated!')
            return redirect('consent_log_list')
        except Exception:
            messages.error(request, 'Error updating consent log.')
            return redirect('consent_log_edit', pk=pk)
    return render(request, 'consent_log_form.html', {'entry': entry, 'editing': True})

def consent_log_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(ConsentLog, id=pk).delete()
        messages.success(request, 'Consent log deleted!')
    return redirect('consent_log_list')


# ===== Phase 7: Tenant Config =====

def tenant_config_list(request):
    entries = TenantConfig.objects.all().order_by('-created_at')
    return render(request, 'tenant_config_list.html', {'entries': entries})

def tenant_config_add(request):
    if request.method == 'POST':
        try:
            TenantConfig.objects.create(
                tenant_name=request.POST.get('tenant_name', ''),
                is_active=request.POST.get('is_active') == 'on',
                data_isolation_level=request.POST.get('data_isolation_level', ''),
            )
            messages.success(request, 'Tenant config added!')
            return redirect('tenant_config_list')
        except Exception:
            messages.error(request, 'Error adding tenant config.')
            return redirect('tenant_config_add')
    return render(request, 'tenant_config_form.html', {'editing': False})

def tenant_config_edit(request, pk):
    entry = get_object_or_404(TenantConfig, id=pk)
    if request.method == 'POST':
        try:
            entry.tenant_name = request.POST.get('tenant_name', '')
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.data_isolation_level = request.POST.get('data_isolation_level', '')
            entry.save()
            messages.success(request, 'Tenant config updated!')
            return redirect('tenant_config_list')
        except Exception:
            messages.error(request, 'Error updating tenant config.')
            return redirect('tenant_config_edit', pk=pk)
    return render(request, 'tenant_config_form.html', {'entry': entry, 'editing': True})

def tenant_config_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(TenantConfig, id=pk).delete()
        messages.success(request, 'Tenant config deleted!')
    return redirect('tenant_config_list')


# ===== Phase 7: Admin Telemetry =====

def admin_telemetry_list(request):
    entries = AdminTelemetry.objects.all().order_by('-recorded_at')
    return render(request, 'admin_telemetry_list.html', {'entries': entries})

def admin_telemetry_add(request):
    if request.method == 'POST':
        try:
            metric_value = request.POST.get('metric_value', '').strip()
            AdminTelemetry.objects.create(
                metric_name=request.POST.get('metric_name', ''),
                metric_value=float(metric_value) if metric_value else None,
            )
            messages.success(request, 'Admin telemetry added!')
            return redirect('admin_telemetry_list')
        except Exception:
            messages.error(request, 'Error adding admin telemetry.')
            return redirect('admin_telemetry_add')
    return render(request, 'admin_telemetry_form.html', {'editing': False})

def admin_telemetry_edit(request, pk):
    entry = get_object_or_404(AdminTelemetry, id=pk)
    if request.method == 'POST':
        try:
            entry.metric_name = request.POST.get('metric_name', '')
            metric_value = request.POST.get('metric_value', '').strip()
            entry.metric_value = float(metric_value) if metric_value else None
            entry.save()
            messages.success(request, 'Admin telemetry updated!')
            return redirect('admin_telemetry_list')
        except Exception:
            messages.error(request, 'Error updating admin telemetry.')
            return redirect('admin_telemetry_edit', pk=pk)
    return render(request, 'admin_telemetry_form.html', {'entry': entry, 'editing': True})

def admin_telemetry_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(AdminTelemetry, id=pk).delete()
        messages.success(request, 'Admin telemetry deleted!')
    return redirect('admin_telemetry_list')


# ===== Phase 7: API Rate Limit Config =====

def api_rate_limit_list(request):
    entries = APIRateLimitConfig.objects.all().order_by('endpoint')
    return render(request, 'api_rate_limit_list.html', {'entries': entries})

def api_rate_limit_add(request):
    if request.method == 'POST':
        try:
            max_min = request.POST.get('max_requests_per_minute', '').strip()
            max_hr = request.POST.get('max_requests_per_hour', '').strip()
            APIRateLimitConfig.objects.create(
                endpoint=request.POST.get('endpoint', ''),
                max_requests_per_minute=int(max_min) if max_min else None,
                max_requests_per_hour=int(max_hr) if max_hr else None,
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'API rate limit config added!')
            return redirect('api_rate_limit_list')
        except Exception:
            messages.error(request, 'Error adding API rate limit config.')
            return redirect('api_rate_limit_add')
    return render(request, 'api_rate_limit_form.html', {'editing': False})

def api_rate_limit_edit(request, pk):
    entry = get_object_or_404(APIRateLimitConfig, id=pk)
    if request.method == 'POST':
        try:
            entry.endpoint = request.POST.get('endpoint', '')
            max_min = request.POST.get('max_requests_per_minute', '').strip()
            max_hr = request.POST.get('max_requests_per_hour', '').strip()
            entry.max_requests_per_minute = int(max_min) if max_min else None
            entry.max_requests_per_hour = int(max_hr) if max_hr else None
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.save()
            messages.success(request, 'API rate limit config updated!')
            return redirect('api_rate_limit_list')
        except Exception:
            messages.error(request, 'Error updating API rate limit config.')
            return redirect('api_rate_limit_edit', pk=pk)
    return render(request, 'api_rate_limit_form.html', {'entry': entry, 'editing': True})

def api_rate_limit_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(APIRateLimitConfig, id=pk).delete()
        messages.success(request, 'API rate limit config deleted!')
    return redirect('api_rate_limit_list')


# ===== Phase 7: Encryption Keys =====

def encryption_key_list(request):
    entries = EncryptionKey.objects.all().order_by('-created_at')
    return render(request, 'encryption_key_list.html', {'entries': entries})

def encryption_key_add(request):
    if request.method == 'POST':
        try:
            EncryptionKey.objects.create(
                key_identifier=request.POST.get('key_identifier', ''),
                public_key=request.POST.get('public_key', ''),
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'Encryption key added!')
            return redirect('encryption_key_list')
        except Exception:
            messages.error(request, 'Error adding encryption key.')
            return redirect('encryption_key_add')
    return render(request, 'encryption_key_form.html', {'editing': False})

def encryption_key_edit(request, pk):
    entry = get_object_or_404(EncryptionKey, id=pk)
    if request.method == 'POST':
        try:
            entry.key_identifier = request.POST.get('key_identifier', '')
            entry.public_key = request.POST.get('public_key', '')
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.save()
            messages.success(request, 'Encryption key updated!')
            return redirect('encryption_key_list')
        except Exception:
            messages.error(request, 'Error updating encryption key.')
            return redirect('encryption_key_edit', pk=pk)
    return render(request, 'encryption_key_form.html', {'entry': entry, 'editing': True})

def encryption_key_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(EncryptionKey, id=pk).delete()
        messages.success(request, 'Encryption key deleted!')
    return redirect('encryption_key_list')


# ===== Phase 7: Audit Logs =====

def audit_log_list(request):
    entries = AuditLog.objects.all().order_by('-created_at')
    return render(request, 'audit_log_list.html', {'entries': entries})

def audit_log_add(request):
    if request.method == 'POST':
        try:
            AuditLog.objects.create(
                action=request.POST.get('action', ''),
                details=request.POST.get('details', ''),
                ip_address=request.POST.get('ip_address', '') or None,
            )
            messages.success(request, 'Audit log added!')
            return redirect('audit_log_list')
        except Exception:
            messages.error(request, 'Error adding audit log.')
            return redirect('audit_log_add')
    return render(request, 'audit_log_form.html', {'editing': False})

def audit_log_edit(request, pk):
    entry = get_object_or_404(AuditLog, id=pk)
    if request.method == 'POST':
        try:
            entry.action = request.POST.get('action', '')
            entry.details = request.POST.get('details', '')
            entry.ip_address = request.POST.get('ip_address', '') or None
            entry.save()
            messages.success(request, 'Audit log updated!')
            return redirect('audit_log_list')
        except Exception:
            messages.error(request, 'Error updating audit log.')
            return redirect('audit_log_edit', pk=pk)
    return render(request, 'audit_log_form.html', {'entry': entry, 'editing': True})

def audit_log_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(AuditLog, id=pk).delete()
        messages.success(request, 'Audit log deleted!')
    return redirect('audit_log_list')


# ===== Phase 7: Anonymized Data Reports =====

def anonymized_data_list(request):
    entries = AnonymizedDataReport.objects.all().order_by('-generated_at')
    return render(request, 'anonymized_data_list.html', {'entries': entries})

def anonymized_data_add(request):
    if request.method == 'POST':
        try:
            total = request.POST.get('total_records', '').strip()
            AnonymizedDataReport.objects.create(
                report_title=request.POST.get('report_title', ''),
                report_type=request.POST.get('report_type', ''),
                total_records=int(total) if total else 0,
                anonymization_method=request.POST.get('anonymization_method', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Anonymized data report added!')
            return redirect('anonymized_data_list')
        except Exception:
            messages.error(request, 'Error adding anonymized data report.')
            return redirect('anonymized_data_add')
    return render(request, 'anonymized_data_form.html', {'editing': False})

def anonymized_data_edit(request, pk):
    entry = get_object_or_404(AnonymizedDataReport, id=pk)
    if request.method == 'POST':
        try:
            entry.report_title = request.POST.get('report_title', '')
            entry.report_type = request.POST.get('report_type', '')
            total = request.POST.get('total_records', '').strip()
            entry.total_records = int(total) if total else 0
            entry.anonymization_method = request.POST.get('anonymization_method', '')
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Anonymized data report updated!')
            return redirect('anonymized_data_list')
        except Exception:
            messages.error(request, 'Error updating anonymized data report.')
            return redirect('anonymized_data_edit', pk=pk)
    return render(request, 'anonymized_data_form.html', {'entry': entry, 'editing': True})

def anonymized_data_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(AnonymizedDataReport, id=pk).delete()
        messages.success(request, 'Anonymized data report deleted!')
    return redirect('anonymized_data_list')


# ===== Phase 7: Database Scaling Config =====

def database_scaling_list(request):
    entries = DatabaseScalingConfig.objects.all().order_by('-created_at')
    return render(request, 'database_scaling_list.html', {'entries': entries})

def database_scaling_add(request):
    if request.method == 'POST':
        try:
            max_conn = request.POST.get('max_connections', '').strip()
            DatabaseScalingConfig.objects.create(
                config_name=request.POST.get('config_name', ''),
                scaling_type=request.POST.get('scaling_type', ''),
                is_active=request.POST.get('is_active') == 'on',
                max_connections=int(max_conn) if max_conn else 100,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Database scaling config added!')
            return redirect('database_scaling_list')
        except Exception:
            messages.error(request, 'Error adding database scaling config.')
            return redirect('database_scaling_add')
    return render(request, 'database_scaling_form.html', {'editing': False})

def database_scaling_edit(request, pk):
    entry = get_object_or_404(DatabaseScalingConfig, id=pk)
    if request.method == 'POST':
        try:
            entry.config_name = request.POST.get('config_name', '')
            entry.scaling_type = request.POST.get('scaling_type', '')
            entry.is_active = request.POST.get('is_active') == 'on'
            max_conn = request.POST.get('max_connections', '').strip()
            entry.max_connections = int(max_conn) if max_conn else 100
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Database scaling config updated!')
            return redirect('database_scaling_list')
        except Exception:
            messages.error(request, 'Error updating database scaling config.')
            return redirect('database_scaling_edit', pk=pk)
    return render(request, 'database_scaling_form.html', {'entry': entry, 'editing': True})

def database_scaling_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(DatabaseScalingConfig, id=pk).delete()
        messages.success(request, 'Database scaling config deleted!')
    return redirect('database_scaling_list')


# ===== Phase 7: Backup Configuration =====

def backup_config_list(request):
    entries = BackupConfiguration.objects.all().order_by('-created_at')
    return render(request, 'backup_config_list.html', {'entries': entries})

def backup_config_add(request):
    if request.method == 'POST':
        try:
            ret = request.POST.get('retention_days', '').strip()
            BackupConfiguration.objects.create(
                backup_name=request.POST.get('backup_name', ''),
                frequency=request.POST.get('frequency', ''),
                retention_days=int(ret) if ret else 30,
                is_active=request.POST.get('is_active') == 'on',
                storage_location=request.POST.get('storage_location', ''),
            )
            messages.success(request, 'Backup configuration added!')
            return redirect('backup_config_list')
        except Exception:
            messages.error(request, 'Error adding backup configuration.')
            return redirect('backup_config_add')
    return render(request, 'backup_config_form.html', {'editing': False})

def backup_config_edit(request, pk):
    entry = get_object_or_404(BackupConfiguration, id=pk)
    if request.method == 'POST':
        try:
            entry.backup_name = request.POST.get('backup_name', '')
            entry.frequency = request.POST.get('frequency', '')
            ret = request.POST.get('retention_days', '').strip()
            entry.retention_days = int(ret) if ret else 30
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.storage_location = request.POST.get('storage_location', '')
            entry.save()
            messages.success(request, 'Backup configuration updated!')
            return redirect('backup_config_list')
        except Exception:
            messages.error(request, 'Error updating backup configuration.')
            return redirect('backup_config_edit', pk=pk)
    return render(request, 'backup_config_form.html', {'entry': entry, 'editing': True})

def backup_config_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(BackupConfiguration, id=pk).delete()
        messages.success(request, 'Backup configuration deleted!')
    return redirect('backup_config_list')


# ===== Phase 8: Medication Schedule =====

def medication_schedule_list(request):
    entries = MedicationSchedule.objects.all().order_by('-start_date')

    # Search by medication name
    search_query = request.GET.get('q', '')
    if search_query:
        entries = entries.filter(medication_name__icontains=search_query)

    # Filter by active status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        entries = entries.filter(is_active=True)
    elif status_filter == 'inactive':
        entries = entries.filter(is_active=False)

    overdue_count = sum(1 for e in entries if e.is_overdue)

    # Summary statistics
    total_active = entries.filter(is_active=True).count()
    total_count = entries.count()

    # Pagination
    paginator = Paginator(entries, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'overdue_count': overdue_count,
        'total_active': total_active,
        'total_count': total_count,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'medication_schedule_list.html', context)

def medication_schedule_add(request):
    if request.method == 'POST':
        try:
            start_str = request.POST.get('start_date', '').strip()
            end_str = request.POST.get('end_date', '').strip()
            MedicationSchedule.objects.create(
                medication_name=request.POST.get('medication_name', ''),
                dosage=request.POST.get('dosage', ''),
                frequency=request.POST.get('frequency', ''),
                start_date=datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else None,
                end_date=datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else None,
                time_of_day=request.POST.get('time_of_day', ''),
                is_active=request.POST.get('is_active') == 'on',
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Medication schedule added!')
            return redirect('medication_schedule_list')
        except Exception:
            messages.error(request, 'Error adding medication schedule.')
            return redirect('medication_schedule_add')
    return render(request, 'medication_schedule_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

def medication_schedule_edit(request, pk):
    entry = get_object_or_404(MedicationSchedule, id=pk)
    if request.method == 'POST':
        try:
            start_str = request.POST.get('start_date', '').strip()
            end_str = request.POST.get('end_date', '').strip()
            entry.medication_name = request.POST.get('medication_name', '')
            entry.dosage = request.POST.get('dosage', '')
            entry.frequency = request.POST.get('frequency', '')
            entry.start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else None
            entry.end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else None
            entry.time_of_day = request.POST.get('time_of_day', '')
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Medication schedule updated!')
            return redirect('medication_schedule_list')
        except Exception:
            messages.error(request, 'Error updating medication schedule.')
            return redirect('medication_schedule_edit', pk=pk)
    return render(request, 'medication_schedule_form.html', {'entry': entry, 'editing': True})

def medication_schedule_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(MedicationSchedule, id=pk).delete()
        messages.success(request, 'Medication schedule deleted!')
    return redirect('medication_schedule_list')


# ===== Phase 8: Health Goal =====

def health_goal_list(request):
    entries = HealthGoal.objects.all().order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        entries = entries.filter(status=status_filter)

    # Search by title
    search_query = request.GET.get('q', '')
    if search_query:
        entries = entries.filter(title__icontains=search_query)

    # Summary statistics
    all_goals = HealthGoal.objects.all()
    stats = {
        'total': all_goals.count(),
        'completed': all_goals.filter(status='completed').count(),
        'in_progress': all_goals.filter(status='active').count(),
        'paused': all_goals.filter(status='paused').count(),
    }
    stats['completion_rate'] = round((stats['completed'] / stats['total']) * 100, 1) if stats['total'] > 0 else 0

    # Pagination
    paginator = Paginator(entries, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'health_goal_list.html', context)

def health_goal_add(request):
    if request.method == 'POST':
        try:
            target_val = request.POST.get('target_value', '').strip()
            current_val = request.POST.get('current_value', '').strip()
            start_str = request.POST.get('start_date', '').strip()
            target_str = request.POST.get('target_date', '').strip()
            HealthGoal.objects.create(
                title=request.POST.get('title', ''),
                description=request.POST.get('description', ''),
                target_value=float(target_val) if target_val else None,
                current_value=float(current_val) if current_val else None,
                unit=request.POST.get('unit', ''),
                status=request.POST.get('status', ''),
                start_date=datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else None,
                target_date=datetime.strptime(target_str, '%Y-%m-%d').date() if target_str else None,
            )
            messages.success(request, 'Health goal added!')
            return redirect('health_goal_list')
        except Exception:
            messages.error(request, 'Error adding health goal.')
            return redirect('health_goal_add')
    return render(request, 'health_goal_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

def health_goal_edit(request, pk):
    entry = get_object_or_404(HealthGoal, id=pk)
    if request.method == 'POST':
        try:
            target_val = request.POST.get('target_value', '').strip()
            current_val = request.POST.get('current_value', '').strip()
            start_str = request.POST.get('start_date', '').strip()
            target_str = request.POST.get('target_date', '').strip()
            entry.title = request.POST.get('title', '')
            entry.description = request.POST.get('description', '')
            entry.target_value = float(target_val) if target_val else None
            entry.current_value = float(current_val) if current_val else None
            entry.unit = request.POST.get('unit', '')
            entry.status = request.POST.get('status', '')
            entry.start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else None
            entry.target_date = datetime.strptime(target_str, '%Y-%m-%d').date() if target_str else None
            entry.save()
            messages.success(request, 'Health goal updated!')
            return redirect('health_goal_list')
        except Exception:
            messages.error(request, 'Error updating health goal.')
            return redirect('health_goal_edit', pk=pk)
    return render(request, 'health_goal_form.html', {'entry': entry, 'editing': True})

def health_goal_delete(request, pk):
    if request.method == 'POST':
        device = get_object_or_404(WearableDevice, id=pk)
        device.access_token = ''
        device.refresh_token = ''
        device.token_expires_at = None
        device.scope = ''
        device.save(update_fields=['access_token', 'refresh_token', 'token_expires_at', 'scope'])
        messages.success(request, f'{device.get_platform_display()} disconnected.')
    return redirect('wearable_device_list')


@login_required
def wearable_sync(request, pk):
    """Trigger a data sync for a wearable device."""
    if request.method == 'POST':
        device = get_object_or_404(WearableDevice, id=pk)
        if not device.access_token:
            messages.error(request, f'{device.get_platform_display()} is not connected. Please connect first.')
            return redirect('wearable_device_list')

        from tracker.integrations.registry import get_client
        client = get_client(device.platform)
        if not client:
            messages.error(request, f'No integration client for {device.get_platform_display()}.')
            return redirect('wearable_device_list')

        sync_log = client.sync_data(device)
        if sync_log.status == 'success':
            messages.success(request, f'Synced {sync_log.records_synced} records from {device.get_platform_display()}.')
        else:
            messages.error(request, f'Sync failed: {sync_log.error_message}')
    return redirect('wearable_device_list')


# ===== Phase 6: Sleep & Circadian =====


def critical_alert_auto_check(request):
    if request.method == 'POST':
        new_alerts = CriticalAlert.check_and_create_alerts()
        if new_alerts:
            messages.success(request, f'{len(new_alerts)} new alert(s) generated from health data.')
        else:
            messages.info(request, 'No new alerts — all health metrics are within normal range.')
    return redirect('critical_alert_list')


# ===== Phase 8: Health Report =====


def health_report_generate(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'monthly')
        period_start_str = request.POST.get('period_start', '').strip()
        period_end_str = request.POST.get('period_end', '').strip()
        try:
            period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
            report = HealthReport.generate_from_data(report_type, period_start, period_end)
            messages.success(request, f'Health report generated: {report.title}')
        except Exception:
            messages.error(request, 'Error generating report. Please provide valid dates.')
    return redirect('health_report_list')


# ===== Phase 8: Biological Age Calculation =====


def biological_age_estimate(request):
    if request.method == 'POST':
        try:
            chrono_age = float(request.POST.get('chronological_age', '0').strip())
            calc = BiologicalAgeCalculation.estimate_from_health_data(chrono_age)
            if calc:
                messages.success(request, f'Biological age estimated: {calc.biological_age} years (difference: {calc.age_difference:+.1f} years).')
            else:
                messages.warning(request, 'Insufficient health data to estimate biological age. Please add vitals, sleep, or metabolic data first.')
        except Exception:
            messages.error(request, 'Error estimating biological age.')
    return redirect('biological_age_list')


# ===== Phase 8: Predictive Biomarker =====


def predictive_biomarker_generate(request):
    if request.method == 'POST':
        biomarker_name = request.POST.get('biomarker_name', '').strip()
        pred_date_str = request.POST.get('prediction_date', '').strip()
        try:
            prediction_date = datetime.strptime(pred_date_str, '%Y-%m-%d').date()
            prediction = PredictiveBiomarker.generate_from_history(biomarker_name, prediction_date)
            if prediction:
                messages.success(request, f'Prediction generated for {biomarker_name}: {prediction.predicted_value} (confidence: {prediction.confidence_percent}%).')
            else:
                messages.warning(request, f'Insufficient data for {biomarker_name}. Need at least 2 historical blood test values.')
        except Exception:
            messages.error(request, 'Error generating prediction. Please provide valid inputs.')
    return redirect('predictive_biomarker_list')


# ===== Phase 9: Secure Viewing Link =====


def secure_link_shared_view(request, token):
    """Public view for accessing shared health data via secure link."""
    link = get_object_or_404(SecureViewingLink, token=token)
    if not link.is_valid:
        return render(request, 'secure_link_expired.html', {'link': link})
    link.access_count += 1
    link.save(update_fields=['access_count'])
    data_types = [dt.strip() for dt in link.data_types.split(',') if dt.strip()] if link.data_types else []
    context = {'link': link, 'data': {}}
    if not data_types or 'blood_tests' in data_types:
        context['data']['blood_tests'] = list(BloodTest.objects.all().order_by('-date')[:20].values(
            'test_name', 'value', 'unit', 'date', 'normal_min', 'normal_max'))
    if not data_types or 'vitals' in data_types:
        context['data']['vitals'] = list(VitalSign.objects.all().order_by('-date')[:20].values(
            'date', 'systolic_bp', 'diastolic_bp', 'heart_rate', 'bbt', 'respiratory_rate', 'spo2'))
    if not data_types or 'medications' in data_types:
        context['data']['medications'] = list(MedicationSchedule.objects.all().order_by('-start_date')[:20].values(
            'medication_name', 'dosage', 'frequency', 'start_date', 'end_date'))
    return render(request, 'secure_link_shared_view.html', context)


# ===== Phase 9: Practitioner Access =====


def practitioner_portal(request):
    """Dedicated portal for practitioners to request access and view patient data."""
    context = {'access_entries': [], 'error': None}
    if request.method == 'POST':
        email = request.POST.get('practitioner_email', '').strip()
        if email:
            entries = PractitionerAccess.objects.filter(
                practitioner_email=email, access_status='approved'
            )
            if entries.exists():
                data = {
                    'blood_tests': list(BloodTest.objects.all().order_by('-date')[:20].values(
                        'test_name', 'value', 'unit', 'date', 'normal_min', 'normal_max')),
                    'vitals': list(VitalSign.objects.all().order_by('-date')[:20].values(
                        'date', 'systolic_bp', 'diastolic_bp', 'heart_rate', 'bbt',
                        'respiratory_rate', 'spo2')),
                    'medications': list(MedicationSchedule.objects.all().order_by('-start_date')[:20].values(
                        'medication_name', 'dosage', 'frequency', 'start_date', 'end_date')),
                }
                context['access_entries'] = entries
                context['patient_data'] = data
            else:
                context['error'] = 'No approved access found for this email address.'
        else:
            context['error'] = 'Please provide a valid email address.'
    return render(request, 'practitioner_portal.html', context)


def practitioner_request_access(request):
    """Allow a practitioner to request access to patient data."""
    if request.method == 'POST':
        name = request.POST.get('practitioner_name', '').strip()
        email = request.POST.get('practitioner_email', '').strip()
        specialty = request.POST.get('specialty', '').strip()
        if name and email:
            PractitionerAccess.objects.create(
                practitioner_name=name,
                practitioner_email=email,
                specialty=specialty,
                access_status='pending',
            )
            messages.success(request, 'Access request submitted. Awaiting patient approval.')
            return redirect('practitioner_portal')
        else:
            messages.error(request, 'Name and email are required.')
    return render(request, 'practitioner_request_access.html')


# ===== Phase 9: Intake Summary =====


def intake_summary_generate(request):
    """Auto-generate an intake summary from existing health data."""
    blood_tests = BloodTest.objects.all().order_by('-date')[:10]
    vitals = VitalSign.objects.all().order_by('-date').first()
    medications = MedicationSchedule.objects.all().order_by('-start_date')

    summary_lines = []
    if vitals:
        parts = []
        if vitals.systolic_bp and vitals.diastolic_bp:
            parts.append(f"BP: {vitals.systolic_bp}/{vitals.diastolic_bp} mmHg")
        if vitals.heart_rate:
            parts.append(f"HR: {vitals.heart_rate} bpm")
        if vitals.bbt:
            parts.append(f"Temp: {vitals.bbt}°C")
        if vitals.spo2:
            parts.append(f"SpO2: {vitals.spo2}%")
        if parts:
            summary_lines.append("Latest Vitals: " + ", ".join(parts))

    if blood_tests:
        test_strs = [f"{t.test_name}: {t.value} {t.unit}" for t in blood_tests[:5]]
        summary_lines.append("Recent Labs: " + "; ".join(test_strs))

    med_list = [f"{m.medication_name} ({m.dosage}, {m.frequency})" for m in medications if m.medication_name]

    conditions_text = ""
    out_of_range = []
    for t in blood_tests:
        if t.normal_min is not None and t.normal_max is not None:
            if t.value < t.normal_min or t.value > t.normal_max:
                out_of_range.append(f"{t.test_name}: {t.value} {t.unit} (range: {t.normal_min}-{t.normal_max})")
    if out_of_range:
        conditions_text = "Out-of-range results: " + "; ".join(out_of_range)

    title = f"Intake Summary - {timezone.now().strftime('%Y-%m-%d')}"
    summary = IntakeSummary.objects.create(
        title=title,
        summary_text="\n".join(summary_lines) if summary_lines else "No health data available.",
        conditions=conditions_text,
        medications="; ".join(med_list) if med_list else "None recorded",
        allergies="",
    )
    messages.success(request, f'Intake summary "{summary.title}" generated from health data!')
    return redirect('intake_summary_list')


# ===== Phase 9: Data Export Request =====

def _collect_export_data():
    """Collect all health data for export."""
    data = {
        'blood_tests': list(BloodTest.objects.all().order_by('-date').values(
            'test_name', 'value', 'unit', 'date', 'normal_min', 'normal_max', 'category')),
        'vitals': list(VitalSign.objects.all().order_by('-date').values(
            'date', 'systolic_bp', 'diastolic_bp', 'heart_rate', 'bbt',
            'respiratory_rate', 'spo2')),
        'medications': list(MedicationSchedule.objects.all().order_by('-start_date').values(
            'medication_name', 'dosage', 'frequency', 'start_date', 'end_date')),
        'body_composition': list(BodyComposition.objects.all().order_by('-date').values(
            'date', 'body_fat_percentage', 'skeletal_muscle_mass', 'waist_circumference',
            'hip_circumference', 'waist_to_hip_ratio')),
        'sleep_logs': list(SleepLog.objects.all().order_by('-date').values(
            'date', 'total_sleep_minutes', 'deep_sleep_minutes', 'rem_minutes',
            'sleep_quality_score')),
    }
    # Convert date objects to strings for JSON serialization
    for key in data:
        for record in data[key]:
            for field, value in record.items():
                if hasattr(value, 'isoformat'):
                    record[field] = value.isoformat()
    return data


def _data_to_xml(data):
    """Convert health data dictionary to XML string."""
    root = Element('health_data')
    root.set('exported_at', timezone.now().isoformat())
    for section_name, records in data.items():
        section = SubElement(root, section_name)
        for record in records:
            entry = SubElement(section, 'entry')
            for field, value in record.items():
                field_elem = SubElement(entry, field)
                field_elem.text = str(value) if value is not None else ''
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding='unicode')


def data_export_download(request, pk):
    """Download exported health data in the requested format (JSON or XML)."""
    export_req = get_object_or_404(DataExportRequest, id=pk)
    data = _collect_export_data()

    if export_req.export_format == 'xml':
        xml_content = _data_to_xml(data)
        response = HttpResponse(xml_content, content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="health_export_{export_req.pk}.xml"'
        return response
    else:
        json_content = json.dumps(data, indent=2, default=str)
        response = HttpResponse(json_content, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="health_export_{export_req.pk}.json"'
        return response


# ===== Phase 9: Stakeholder Email =====


def _build_health_summary_text():
    """Build a plain-text health summary for stakeholder emails."""
    lines = ["Health Summary Report", "=" * 40, ""]

    vitals = VitalSign.objects.all().order_by('-date').first()
    if vitals:
        lines.append("Latest Vitals:")
        if vitals.systolic_bp and vitals.diastolic_bp:
            lines.append(f"  Blood Pressure: {vitals.systolic_bp}/{vitals.diastolic_bp} mmHg")
        if vitals.heart_rate:
            lines.append(f"  Heart Rate: {vitals.heart_rate} bpm")
        if vitals.bbt:
            lines.append(f"  Temperature: {vitals.bbt}°C")
        if vitals.spo2:
            lines.append(f"  Oxygen Saturation: {vitals.spo2}%")
        lines.append("")

    blood_tests = BloodTest.objects.all().order_by('-date')[:5]
    if blood_tests:
        lines.append("Recent Lab Results:")
        for t in blood_tests:
            status = ""
            if t.normal_min is not None and t.normal_max is not None:
                if t.value < t.normal_min or t.value > t.normal_max:
                    status = " [OUT OF RANGE]"
            lines.append(f"  {t.test_name}: {t.value} {t.unit}{status}")
        lines.append("")

    medications = MedicationSchedule.objects.all().order_by('-start_date')
    if medications:
        lines.append("Current Medications:")
        for m in medications:
            lines.append(f"  {m.medication_name} - {m.dosage} ({m.frequency})")
        lines.append("")

    lines.append(f"Report generated: {timezone.now().strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines)


def stakeholder_email_send(request, pk):
    """Send a health summary email to a specific stakeholder."""
    entry = get_object_or_404(StakeholderEmail, id=pk)
    if not entry.is_active:
        messages.error(request, 'This stakeholder email is not active.')
        return redirect('stakeholder_email_list')

    summary_text = _build_health_summary_text()
    try:
        send_mail(
            subject=f'Health Summary for {entry.recipient_name}',
            message=summary_text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@healthtracker.local'),
            recipient_list=[entry.recipient_email],
            fail_silently=False,
        )
        entry.last_sent = timezone.now()
        entry.save(update_fields=['last_sent'])
        messages.success(request, f'Health summary sent to {entry.recipient_email}!')
    except Exception as e:
        messages.error(request, f'Error sending email: {e}')
    return redirect('stakeholder_email_list')


# ===== Phase 10-12: Integration Config =====


def integration_config_activate(request, pk):
    entry = get_object_or_404(IntegrationConfig, id=pk)
    if request.method == 'POST':
        success, msg = entry.activate()
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('integration_config_list')

def integration_config_run(request, pk):
    entry = get_object_or_404(IntegrationConfig, id=pk)
    if request.method == 'POST':
        success, msg = entry.run_integration()
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('integration_config_list')


# ===== Phase 10-12: Integration Sub-Task =====


def phase11_dashboard(request):
    subtasks = IntegrationSubTask.objects.filter(phase=11).order_by('sub_task_number')

    category_filter = request.GET.get('category', '')
    feature_type_filter = request.GET.get('feature_type', '')
    status_filter = request.GET.get('status', '')

    if category_filter:
        subtasks = subtasks.filter(category=category_filter)
    if feature_type_filter:
        subtasks = subtasks.filter(feature_type=feature_type_filter)
    if status_filter:
        subtasks = subtasks.filter(status=status_filter)

    all_phase11 = IntegrationSubTask.objects.filter(phase=11)
    total = all_phase11.count()
    completed = all_phase11.filter(status='completed').count()
    in_progress = all_phase11.filter(status='in_progress').count()
    pending = all_phase11.filter(status='pending').count()
    failed = all_phase11.filter(status='failed').count()

    category_summary = {}
    for cat_key, cat_label in INTEGRATION_CATEGORIES:
        cat_tasks = all_phase11.filter(category=cat_key)
        count = cat_tasks.count()
        if count > 0:
            category_summary[cat_label] = {
                'total': count,
                'completed': cat_tasks.filter(status='completed').count(),
                'in_progress': cat_tasks.filter(status='in_progress').count(),
                'pending': cat_tasks.filter(status='pending').count(),
            }

    context = {
        'subtasks': subtasks,
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'failed': failed,
        'categories': INTEGRATION_CATEGORIES,
        'feature_types': INTEGRATION_FEATURE_TYPES,
        'status_choices': IntegrationSubTask.STATUS_CHOICES,
        'category_filter': category_filter,
        'feature_type_filter': feature_type_filter,
        'status_filter': status_filter,
        'category_summary': category_summary,
    }
    return render(request, 'phase11_dashboard.html', context)



# ===================================================================
# Generic CRUD registrations (replaces individual CRUD view functions)
# ===================================================================

# ===== Body Composition =====
_body_composition = make_crud_views(
    model_class=BodyComposition,
    display_name='Body Composition',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'body_fat_percentage', 'type': 'float', 'step': '0.1', 'placeholder': 'e.g. 18.5', 'label': 'Body Fat (%)'},
        {'name': 'skeletal_muscle_mass', 'type': 'float', 'step': '0.1', 'placeholder': 'e.g. 30.0', 'label': 'Skeletal Muscle Mass (kg)'},
        {'name': 'bone_density', 'type': 'float', 'step': '0.01', 'placeholder': 'e.g. 1.2', 'label': 'Bone Density (g/cm²)'},
        {'name': 'waist_circumference', 'type': 'float', 'step': '0.1', 'placeholder': 'e.g. 80', 'label': 'Waist (cm)'},
        {'name': 'hip_circumference', 'type': 'float', 'step': '0.1', 'placeholder': 'e.g. 95', 'label': 'Hip (cm)'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='body_composition_list',
    add_url_name='body_composition_add',
    edit_url_name='body_composition_edit',
)
body_composition_add = _body_composition['add']
body_composition_edit = _body_composition['edit']
body_composition_delete = _body_composition['delete']

# ===== Hydration =====
_hydration = make_crud_views(
    model_class=HydrationLog,
    display_name='Hydration',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'fluid_intake_ml', 'type': 'float', 'default': 0, 'placeholder': 'e.g. 2000', 'label': 'Fluid Intake (ml)'},
        {'name': 'goal_ml', 'type': 'float', 'default': 2500, 'placeholder': 'e.g. 2500', 'label': 'Goal (ml)'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='hydration_list',
    add_url_name='hydration_add',
    edit_url_name='hydration_edit',
)
hydration_add = _hydration['add']
hydration_edit = _hydration['edit']
hydration_delete = _hydration['delete']

# ===== Energy & Fatigue =====
_energy = make_crud_views(
    model_class=EnergyFatigueLog,
    display_name='Energy & Fatigue',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'energy_score', 'type': 'int', 'default': 5, 'placeholder': '1-10', 'label': 'Energy Score'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='energy_list',
    add_url_name='energy_add',
    edit_url_name='energy_edit',
)
energy_list = _energy['list']
energy_add = _energy['add']
energy_edit = _energy['edit']
energy_delete = _energy['delete']

# ===== Pain =====
_pain = make_crud_views(
    model_class=PainLog,
    display_name='Pain Log',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'body_region', 'type': 'str', 'choices': BODY_REGIONS, 'label': 'Body Region'},
        {'name': 'pain_level', 'type': 'int', 'default': 1, 'placeholder': '1-10', 'label': 'Pain Level'},
        {'name': 'description', 'type': 'str', 'widget': 'textarea', 'label': 'Description'},
    ],
    list_url_name='pain_list',
    add_url_name='pain_add',
    edit_url_name='pain_edit',
    extra_list_context={'body_regions': BODY_REGIONS},
    extra_form_context={'body_regions': BODY_REGIONS},
    list_template='pain_list.html',
)
pain_list = _pain['list']
pain_add = _pain['add']
pain_edit = _pain['edit']
pain_delete = _pain['delete']

# ===== RMR =====
_rmr = make_crud_views(
    model_class=RestingMetabolicRate,
    display_name='Resting Metabolic Rate',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'age', 'type': 'int', 'required': True, 'label': 'Age'},
        {'name': 'weight_kg', 'type': 'float', 'required': True, 'default': 0, 'label': 'Weight (kg)'},
        {'name': 'height_cm', 'type': 'float', 'required': True, 'default': 0, 'label': 'Height (cm)'},
        {'name': 'gender', 'type': 'str', 'choices': RestingMetabolicRate.GENDER_CHOICES, 'default': 'M', 'label': 'Gender'},
        {'name': 'formula', 'type': 'str', 'choices': RestingMetabolicRate.FORMULA_CHOICES, 'default': 'mifflin', 'label': 'Formula'},
    ],
    list_url_name='rmr_list',
    add_url_name='rmr_add',
    edit_url_name='rmr_edit',
)
rmr_list = _rmr['list']
rmr_add = _rmr['add']
rmr_edit = _rmr['edit']
rmr_delete = _rmr['delete']

# ===== Orthostatic =====
_orthostatic = make_crud_views(
    model_class=OrthostaticReading,
    display_name='Orthostatic Reading',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'supine_hr', 'type': 'int', 'label': 'Supine HR'},
        {'name': 'standing_hr', 'type': 'int', 'label': 'Standing HR'},
        {'name': 'supine_systolic', 'type': 'int', 'label': 'Supine Systolic'},
        {'name': 'supine_diastolic', 'type': 'int', 'label': 'Supine Diastolic'},
        {'name': 'standing_systolic', 'type': 'int', 'label': 'Standing Systolic'},
        {'name': 'standing_diastolic', 'type': 'int', 'label': 'Standing Diastolic'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='orthostatic_list',
    add_url_name='orthostatic_add',
    edit_url_name='orthostatic_edit',
)
orthostatic_list = _orthostatic['list']
orthostatic_add = _orthostatic['add']
orthostatic_edit = _orthostatic['edit']
orthostatic_delete = _orthostatic['delete']

# ===== Reproductive Health =====
_reproductive = make_crud_views(
    model_class=ReproductiveHealthLog,
    display_name='Reproductive Health',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'cycle_day', 'type': 'int', 'label': 'Cycle Day'},
        {'name': 'phase', 'type': 'str', 'choices': ReproductiveHealthLog.PHASE_CHOICES, 'label': 'Phase'},
        {'name': 'flow_intensity', 'type': 'int', 'placeholder': '0-5', 'label': 'Flow Intensity'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='reproductive_list',
    add_url_name='reproductive_add',
    edit_url_name='reproductive_edit',
)
reproductive_list = _reproductive['list']
reproductive_add = _reproductive['add']
reproductive_edit = _reproductive['edit']
reproductive_delete = _reproductive['delete']

# ===== Symptom Journal =====
_symptom = make_crud_views(
    model_class=SymptomJournal,
    display_name='Symptom Journal',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'symptom', 'type': 'str', 'required': True, 'label': 'Symptom'},
        {'name': 'severity', 'type': 'int', 'choices': SymptomJournal.SEVERITY_CHOICES, 'default': 1, 'label': 'Severity'},
        {'name': 'duration', 'type': 'str', 'label': 'Duration'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='symptom_list',
    add_url_name='symptom_add',
    edit_url_name='symptom_edit',
)
symptom_list = _symptom['list']
symptom_add = _symptom['add']
symptom_edit = _symptom['edit']
symptom_delete = _symptom['delete']

# ===== Metabolic =====
_metabolic = make_crud_views(
    model_class=MetabolicLog,
    display_name='Glucose & Insulin',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'blood_glucose', 'type': 'float', 'label': 'Blood Glucose'},
        {'name': 'insulin_level', 'type': 'float', 'label': 'Insulin Level'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='metabolic_list',
    add_url_name='metabolic_add',
    edit_url_name='metabolic_edit',
)
metabolic_list = _metabolic['list']
metabolic_add = _metabolic['add']
metabolic_edit = _metabolic['edit']
metabolic_delete = _metabolic['delete']

# ===== Ketone =====
_ketone = make_crud_views(
    model_class=KetoneLog,
    display_name='Ketone',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'value', 'type': 'float', 'required': True, 'label': 'Value'},
        {'name': 'measurement_type', 'type': 'str', 'choices': KetoneLog.MEASUREMENT_CHOICES, 'default': 'blood', 'label': 'Measurement Type'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='ketone_list',
    add_url_name='ketone_add',
    edit_url_name='ketone_edit',
)
ketone_list = _ketone['list']
ketone_add = _ketone['add']
ketone_edit = _ketone['edit']
ketone_delete = _ketone['delete']

# ===== Sleep =====
_sleep = make_crud_views(
    model_class=SleepLog,
    display_name='Sleep',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'bedtime', 'type': 'time', 'label': 'Bedtime'},
        {'name': 'wake_time', 'type': 'time', 'label': 'Wake Time'},
        {'name': 'total_sleep_minutes', 'type': 'int', 'label': 'Total Sleep (min)'},
        {'name': 'rem_minutes', 'type': 'int', 'label': 'REM (min)'},
        {'name': 'deep_sleep_minutes', 'type': 'int', 'label': 'Deep Sleep (min)'},
        {'name': 'light_sleep_minutes', 'type': 'int', 'label': 'Light Sleep (min)'},
        {'name': 'awake_minutes', 'type': 'int', 'label': 'Awake (min)'},
        {'name': 'sleep_quality_score', 'type': 'float', 'step': '0.1', 'placeholder': '1-10', 'label': 'Quality Score'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='sleep_list',
    add_url_name='sleep_add',
    edit_url_name='sleep_edit',
)
sleep_add = _sleep['add']
sleep_edit = _sleep['edit']
sleep_delete = _sleep['delete']

# ===== Circadian Rhythm =====
_circadian = make_crud_views(
    model_class=CircadianRhythmLog,
    display_name='Circadian Rhythm',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'wake_time', 'type': 'time', 'label': 'Wake Time'},
        {'name': 'sleep_onset', 'type': 'time', 'label': 'Sleep Onset'},
        {'name': 'peak_energy_time', 'type': 'time', 'label': 'Peak Energy Time'},
        {'name': 'lowest_energy_time', 'type': 'time', 'label': 'Lowest Energy Time'},
        {'name': 'light_exposure_minutes', 'type': 'int', 'label': 'Light Exposure (min)'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='circadian_list',
    add_url_name='circadian_add',
    edit_url_name='circadian_edit',
)
circadian_list = _circadian['list']
circadian_add = _circadian['add']
circadian_edit = _circadian['edit']
circadian_delete = _circadian['delete']

# ===== Dream Journal =====
_dream = make_crud_views(
    model_class=DreamJournal,
    display_name='Dream Journal',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'dream_description', 'type': 'str', 'widget': 'textarea', 'label': 'Dream Description'},
        {'name': 'lucidity_level', 'type': 'int', 'placeholder': '0-5', 'label': 'Lucidity Level'},
        {'name': 'mood_on_waking', 'type': 'str', 'label': 'Mood on Waking'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='dream_list',
    add_url_name='dream_add',
    edit_url_name='dream_edit',
)
dream_list = _dream['list']
dream_add = _dream['add']
dream_edit = _dream['edit']
dream_delete = _dream['delete']

# ===== Macronutrients =====
_macro = make_crud_views(
    model_class=MacronutrientLog,
    display_name='Macronutrients',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'protein_grams', 'type': 'float', 'label': 'Protein (g)'},
        {'name': 'carbohydrate_grams', 'type': 'float', 'label': 'Carbs (g)'},
        {'name': 'fat_grams', 'type': 'float', 'label': 'Fat (g)'},
        {'name': 'calories', 'type': 'float', 'label': 'Calories'},
        {'name': 'fiber_grams', 'type': 'float', 'label': 'Fiber (g)'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='macro_list',
    add_url_name='macro_add',
    edit_url_name='macro_edit',
)
macro_add = _macro['add']
macro_edit = _macro['edit']
macro_delete = _macro['delete']

# ===== Micronutrients =====
_micro = make_crud_views(
    model_class=MicronutrientLog,
    display_name='Micronutrients',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'nutrient_name', 'type': 'str', 'required': True, 'label': 'Nutrient Name'},
        {'name': 'amount', 'type': 'float', 'required': True, 'label': 'Amount'},
        {'name': 'unit', 'type': 'str', 'default': 'mg', 'label': 'Unit'},
        {'name': 'deficiency_risk', 'type': 'str', 'label': 'Deficiency Risk'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='micro_list',
    add_url_name='micro_add',
    edit_url_name='micro_edit',
)
micro_list = _micro['list']
micro_add = _micro['add']
micro_edit = _micro['edit']
micro_delete = _micro['delete']

# ===== Food Entries =====
_food = make_crud_views(
    model_class=FoodEntry,
    display_name='Food Entry',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'food_name', 'type': 'str', 'required': True, 'label': 'Food Name'},
        {'name': 'barcode', 'type': 'str', 'label': 'Barcode'},
        {'name': 'serving_size', 'type': 'str', 'label': 'Serving Size'},
        {'name': 'calories', 'type': 'float', 'label': 'Calories'},
        {'name': 'protein_grams', 'type': 'float', 'label': 'Protein (g)'},
        {'name': 'carbohydrate_grams', 'type': 'float', 'label': 'Carbs (g)'},
        {'name': 'fat_grams', 'type': 'float', 'label': 'Fat (g)'},
        {'name': 'source', 'type': 'str', 'label': 'Source'},
        {'name': 'food_database_id', 'type': 'str', 'label': 'Database ID'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='food_list',
    add_url_name='food_add',
    edit_url_name='food_edit',
)
food_list = _food['list']
food_add = _food['add']
food_edit = _food['edit']
food_delete = _food['delete']

# ===== Fasting =====
_fasting = make_crud_views(
    model_class=FastingLog,
    display_name='Fasting',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'fast_start', 'type': 'datetime', 'label': 'Fast Start'},
        {'name': 'fast_end', 'type': 'datetime', 'label': 'Fast End'},
        {'name': 'target_hours', 'type': 'float', 'label': 'Target Hours'},
        {'name': 'actual_hours', 'type': 'float', 'label': 'Actual Hours'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='fasting_list',
    add_url_name='fasting_add',
    edit_url_name='fasting_edit',
)
fasting_list = _fasting['list']
fasting_add = _fasting['add']
fasting_edit = _fasting['edit']
fasting_delete = _fasting['delete']

# ===== Caffeine & Alcohol =====
_caffeine_alcohol = make_crud_views(
    model_class=CaffeineAlcoholLog,
    display_name='Caffeine & Alcohol',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'substance', 'type': 'str', 'choices': CaffeineAlcoholLog.SUBSTANCE_CHOICES, 'label': 'Substance'},
        {'name': 'amount_mg', 'type': 'float', 'label': 'Amount (mg)'},
        {'name': 'drink_name', 'type': 'str', 'label': 'Drink Name'},
        {'name': 'time_consumed', 'type': 'time', 'label': 'Time Consumed'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='caffeine_alcohol_list',
    add_url_name='caffeine_alcohol_add',
    edit_url_name='caffeine_alcohol_edit',
)
caffeine_alcohol_list = _caffeine_alcohol['list']
caffeine_alcohol_add = _caffeine_alcohol['add']
caffeine_alcohol_edit = _caffeine_alcohol['edit']
caffeine_alcohol_delete = _caffeine_alcohol['delete']

# ===== Medication Schedule =====
_medication = make_crud_views(
    model_class=MedicationSchedule,
    display_name='Medication Schedule',
    fields=[
        {'name': 'medication_name', 'type': 'str', 'required': True, 'label': 'Medication Name'},
        {'name': 'dosage', 'type': 'str', 'required': True, 'label': 'Dosage'},
        {'name': 'frequency', 'type': 'str', 'required': True, 'label': 'Frequency'},
        {'name': 'start_date', 'type': 'date', 'required': True, 'label': 'Start Date'},
        {'name': 'end_date', 'type': 'date', 'label': 'End Date'},
        {'name': 'time_of_day', 'type': 'time', 'label': 'Time of Day'},
        {'name': 'is_active', 'type': 'bool', 'default': True, 'label': 'Active'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='medication_schedule_list',
    add_url_name='medication_schedule_add',
    edit_url_name='medication_schedule_edit',
    order_by='-start_date',
)
medication_schedule_add = _medication['add']
medication_schedule_edit = _medication['edit']
medication_schedule_delete = _medication['delete']

# ===== Health Goals =====
_health_goal = make_crud_views(
    model_class=HealthGoal,
    display_name='Health Goal',
    fields=[
        {'name': 'title', 'type': 'str', 'required': True, 'label': 'Title'},
        {'name': 'description', 'type': 'str', 'widget': 'textarea', 'label': 'Description'},
        {'name': 'target_value', 'type': 'float', 'label': 'Target Value'},
        {'name': 'current_value', 'type': 'float', 'label': 'Current Value'},
        {'name': 'unit', 'type': 'str', 'label': 'Unit'},
        {'name': 'status', 'type': 'str', 'choices': HealthGoal.STATUS_CHOICES, 'default': 'active', 'label': 'Status'},
        {'name': 'start_date', 'type': 'date', 'required': True, 'label': 'Start Date'},
        {'name': 'target_date', 'type': 'date', 'label': 'Target Date'},
    ],
    list_url_name='health_goal_list',
    add_url_name='health_goal_add',
    edit_url_name='health_goal_edit',
    order_by='-start_date',
)
health_goal_add = _health_goal['add']
health_goal_edit = _health_goal['edit']
health_goal_delete = _health_goal['delete']

# ===== Critical Alerts =====
_critical_alert = make_crud_views(
    model_class=CriticalAlert,
    display_name='Critical Alert',
    fields=[
        {'name': 'metric_name', 'type': 'str', 'required': True, 'label': 'Metric Name'},
        {'name': 'metric_value', 'type': 'float', 'required': True, 'label': 'Metric Value'},
        {'name': 'threshold_value', 'type': 'float', 'required': True, 'label': 'Threshold Value'},
        {'name': 'alert_level', 'type': 'str', 'choices': CriticalAlert.ALERT_LEVELS, 'default': 'warning', 'label': 'Alert Level'},
        {'name': 'message', 'type': 'str', 'widget': 'textarea', 'label': 'Message'},
        {'name': 'acknowledged', 'type': 'bool', 'label': 'Acknowledged'},
    ],
    list_url_name='critical_alert_list',
    add_url_name='critical_alert_add',
    edit_url_name='critical_alert_edit',
    order_by='-triggered_at',
)
critical_alert_list = _critical_alert['list']
critical_alert_add = _critical_alert['add']
critical_alert_edit = _critical_alert['edit']
critical_alert_delete = _critical_alert['delete']

# ===== Health Reports =====
_health_report = make_crud_views(
    model_class=HealthReport,
    display_name='Health Report',
    fields=[
        {'name': 'report_type', 'type': 'str', 'choices': HealthReport.REPORT_TYPES, 'default': 'monthly', 'label': 'Report Type'},
        {'name': 'title', 'type': 'str', 'required': True, 'label': 'Title'},
        {'name': 'content', 'type': 'str', 'widget': 'textarea', 'label': 'Content'},
        {'name': 'period_start', 'type': 'date', 'required': True, 'label': 'Period Start'},
        {'name': 'period_end', 'type': 'date', 'required': True, 'label': 'Period End'},
    ],
    list_url_name='health_report_list',
    add_url_name='health_report_add',
    edit_url_name='health_report_edit',
    order_by='-generated_at',
)
health_report_list = _health_report['list']
health_report_add = _health_report['add']
health_report_edit = _health_report['edit']
health_report_delete = _health_report['delete']

# ===== Biological Age =====
_biological_age = make_crud_views(
    model_class=BiologicalAgeCalculation,
    display_name='Biological Age',
    fields=[
        {'name': 'date', 'type': 'date', 'required': True, 'label': 'Date'},
        {'name': 'chronological_age', 'type': 'float', 'required': True, 'label': 'Chronological Age'},
        {'name': 'biological_age', 'type': 'float', 'required': True, 'label': 'Biological Age'},
        {'name': 'method', 'type': 'str', 'label': 'Method'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='biological_age_list',
    add_url_name='biological_age_add',
    edit_url_name='biological_age_edit',
)
biological_age_list = _biological_age['list']
biological_age_add = _biological_age['add']
biological_age_edit = _biological_age['edit']
biological_age_delete = _biological_age['delete']

# ===== Predictive Biomarkers =====
_predictive_biomarker = make_crud_views(
    model_class=PredictiveBiomarker,
    display_name='Predictive Biomarker',
    fields=[
        {'name': 'biomarker_name', 'type': 'str', 'required': True, 'label': 'Biomarker Name'},
        {'name': 'predicted_value', 'type': 'float', 'required': True, 'label': 'Predicted Value'},
        {'name': 'confidence_percent', 'type': 'float', 'label': 'Confidence (%)'},
        {'name': 'prediction_date', 'type': 'date', 'required': True, 'label': 'Prediction Date'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='predictive_biomarker_list',
    add_url_name='predictive_biomarker_add',
    edit_url_name='predictive_biomarker_edit',
    order_by='-prediction_date',
)
predictive_biomarker_list = _predictive_biomarker['list']
predictive_biomarker_add = _predictive_biomarker['add']
predictive_biomarker_edit = _predictive_biomarker['edit']
predictive_biomarker_delete = _predictive_biomarker['delete']

# ===== Secure Viewing Links =====
_secure_viewing_link = make_crud_views(
    model_class=SecureViewingLink,
    display_name='Secure Viewing Link',
    fields=[
        {'name': 'data_types', 'type': 'str', 'label': 'Data Types'},
        {'name': 'expires_at', 'type': 'datetime', 'required': True, 'label': 'Expires At'},
        {'name': 'is_active', 'type': 'bool', 'default': True, 'label': 'Active'},
    ],
    list_url_name='secure_viewing_link_list',
    add_url_name='secure_viewing_link_add',
    edit_url_name='secure_viewing_link_edit',
    order_by='-created_at',
)
secure_viewing_link_list = _secure_viewing_link['list']
secure_viewing_link_delete = _secure_viewing_link['delete']

def secure_viewing_link_add(request):
    if request.method == 'POST':
        try:
            expires_str = request.POST.get('expires_at', '').strip()
            expires_dt = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M') if expires_str else None
            SecureViewingLink.objects.create(
                token=SecureViewingLink.generate_token(),
                data_types=request.POST.get('data_types', ''),
                expires_at=expires_dt,
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'Secure viewing link created!')
            return redirect('secure_viewing_link_list')
        except Exception:
            messages.error(request, 'Error creating secure viewing link.')
            return redirect('secure_viewing_link_add')
    return render(request, 'secure_viewing_link_form.html', {'editing': False})

def secure_viewing_link_edit(request, pk):
    entry = get_object_or_404(SecureViewingLink, id=pk)
    if request.method == 'POST':
        try:
            expires_str = request.POST.get('expires_at', '').strip()
            entry.data_types = request.POST.get('data_types', '')
            entry.expires_at = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M') if expires_str else entry.expires_at
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.save()
            messages.success(request, 'Secure viewing link updated!')
            return redirect('secure_viewing_link_list')
        except Exception:
            messages.error(request, 'Error updating secure viewing link.')
            return redirect('secure_viewing_link_edit', pk=pk)
    return render(request, 'secure_viewing_link_form.html', {'entry': entry, 'editing': True})

# ===== Practitioner Access =====
_practitioner_access = make_crud_views(
    model_class=PractitionerAccess,
    display_name='Practitioner Access',
    fields=[
        {'name': 'practitioner_name', 'type': 'str', 'required': True, 'label': 'Practitioner Name'},
        {'name': 'practitioner_email', 'type': 'str', 'required': True, 'label': 'Email'},
        {'name': 'specialty', 'type': 'str', 'label': 'Specialty'},
        {'name': 'access_status', 'type': 'str', 'choices': PractitionerAccess.ACCESS_STATUS, 'default': 'pending', 'label': 'Status'},
        {'name': 'expires_at', 'type': 'datetime', 'label': 'Expires At'},
    ],
    list_url_name='practitioner_access_list',
    add_url_name='practitioner_access_add',
    edit_url_name='practitioner_access_edit',
    order_by='-granted_at',
)
practitioner_access_list = _practitioner_access['list']
practitioner_access_add = _practitioner_access['add']
practitioner_access_delete = _practitioner_access['delete']

def practitioner_access_edit(request, pk):
    entry = get_object_or_404(PractitionerAccess, id=pk)
    if request.method == 'POST':
        try:
            entry.practitioner_name = request.POST.get('practitioner_name', '')
            entry.practitioner_email = request.POST.get('practitioner_email', '')
            entry.specialty = request.POST.get('specialty', '')
            new_status = request.POST.get('access_status', entry.access_status)
            if new_status == 'approved' and entry.access_status != 'approved':
                entry.granted_at = timezone.now()
            entry.access_status = new_status
            entry.save()
            messages.success(request, 'Practitioner access updated!')
            return redirect('practitioner_access_list')
        except Exception:
            messages.error(request, 'Error updating practitioner access.')
            return redirect('practitioner_access_edit', pk=pk)
    return render(request, 'practitioner_access_form.html', {'entry': entry, 'editing': True})

# ===== Intake Summaries =====
_intake_summary = make_crud_views(
    model_class=IntakeSummary,
    display_name='Intake Summary',
    fields=[
        {'name': 'title', 'type': 'str', 'required': True, 'label': 'Title'},
        {'name': 'summary_text', 'type': 'str', 'widget': 'textarea', 'label': 'Summary'},
        {'name': 'conditions', 'type': 'str', 'widget': 'textarea', 'label': 'Conditions'},
        {'name': 'medications', 'type': 'str', 'widget': 'textarea', 'label': 'Medications'},
        {'name': 'allergies', 'type': 'str', 'widget': 'textarea', 'label': 'Allergies'},
    ],
    list_url_name='intake_summary_list',
    add_url_name='intake_summary_add',
    edit_url_name='intake_summary_edit',
    order_by='-generated_at',
)
intake_summary_list = _intake_summary['list']
intake_summary_add = _intake_summary['add']
intake_summary_edit = _intake_summary['edit']
intake_summary_delete = _intake_summary['delete']

# ===== Data Export =====
_data_export = make_crud_views(
    model_class=DataExportRequest,
    display_name='Data Export',
    fields=[
        {'name': 'export_format', 'type': 'str', 'choices': DataExportRequest.FORMAT_CHOICES, 'default': 'json', 'label': 'Format'},
        {'name': 'status', 'type': 'str', 'choices': DataExportRequest.STATUS_CHOICES, 'default': 'pending', 'label': 'Status'},
        {'name': 'file_path', 'type': 'str', 'label': 'File Path'},
    ],
    list_url_name='data_export_list',
    add_url_name='data_export_add',
    edit_url_name='data_export_edit',
    order_by='-requested_at',
)
data_export_list = _data_export['list']
data_export_edit = _data_export['edit']
data_export_delete = _data_export['delete']

def data_export_add(request):
    if request.method == 'POST':
        try:
            export_format = request.POST.get('export_format', 'json')
            DataExportRequest.objects.create(
                export_format=export_format,
                status='completed',
                completed_at=timezone.now(),
            )
            messages.success(request, 'Data export created!')
            return redirect('data_export_list')
        except Exception:
            messages.error(request, 'Error creating data export.')
            return redirect('data_export_add')
    return render(request, 'data_export_form.html', {'editing': False})

# ===== Stakeholder Emails =====
_stakeholder_email = make_crud_views(
    model_class=StakeholderEmail,
    display_name='Stakeholder Email',
    fields=[
        {'name': 'recipient_name', 'type': 'str', 'required': True, 'label': 'Recipient Name'},
        {'name': 'recipient_email', 'type': 'str', 'required': True, 'label': 'Recipient Email'},
        {'name': 'frequency', 'type': 'str', 'choices': StakeholderEmail.FREQUENCY_CHOICES, 'default': 'monthly', 'label': 'Frequency'},
        {'name': 'is_active', 'type': 'bool', 'default': True, 'label': 'Active'},
    ],
    list_url_name='stakeholder_email_list',
    add_url_name='stakeholder_email_add',
    edit_url_name='stakeholder_email_edit',
    order_by='-created_at',
)
stakeholder_email_list = _stakeholder_email['list']
stakeholder_email_add = _stakeholder_email['add']
stakeholder_email_edit = _stakeholder_email['edit']
stakeholder_email_delete = _stakeholder_email['delete']

# ===== User Profiles (RBAC) =====
_user_profile = make_crud_views(
    model_class=UserProfile,
    display_name='User Profile',
    fields=[
        {'name': 'role', 'type': 'str', 'choices': UserProfile.ROLE_CHOICES, 'default': 'user', 'label': 'Role'},
    ],
    list_url_name='user_profile_list',
    add_url_name='user_profile_add',
    edit_url_name='user_profile_edit',
    order_by='-created_at',
)
user_profile_list = _user_profile['list']

# ===== Family Accounts =====
_family_account = make_crud_views(
    model_class=FamilyAccount,
    display_name='Family Account',
    fields=[
        {'name': 'member_name', 'type': 'str', 'required': True, 'label': 'Member Name'},
        {'name': 'relationship', 'type': 'str', 'label': 'Relationship'},
        {'name': 'is_minor', 'type': 'bool', 'label': 'Is Minor'},
    ],
    list_url_name='family_account_list',
    add_url_name='family_account_add',
    edit_url_name='family_account_edit',
    order_by='-created_at',
)
family_account_list = _family_account['list']
family_account_add = _family_account['add']
family_account_edit = _family_account['edit']
family_account_delete = _family_account['delete']

# ===== Consent Logs =====
_consent_log = make_crud_views(
    model_class=ConsentLog,
    display_name='Consent Log',
    fields=[
        {'name': 'consent_type', 'type': 'str', 'required': True, 'label': 'Consent Type'},
        {'name': 'version', 'type': 'str', 'required': True, 'label': 'Version'},
        {'name': 'accepted', 'type': 'bool', 'label': 'Accepted'},
        {'name': 'ip_address', 'type': 'str', 'label': 'IP Address'},
    ],
    list_url_name='consent_log_list',
    add_url_name='consent_log_add',
    edit_url_name='consent_log_edit',
    order_by='-accepted_at',
)
consent_log_list = _consent_log['list']
consent_log_add = _consent_log['add']
consent_log_edit = _consent_log['edit']
consent_log_delete = _consent_log['delete']

# ===== Tenant Config =====
_tenant_config = make_crud_views(
    model_class=TenantConfig,
    display_name='Tenant Config',
    fields=[
        {'name': 'tenant_name', 'type': 'str', 'required': True, 'label': 'Tenant Name'},
        {'name': 'is_active', 'type': 'bool', 'default': True, 'label': 'Active'},
        {'name': 'data_isolation_level', 'type': 'str', 'default': 'full', 'label': 'Data Isolation Level'},
    ],
    list_url_name='tenant_config_list',
    add_url_name='tenant_config_add',
    edit_url_name='tenant_config_edit',
    order_by='-created_at',
)
tenant_config_list = _tenant_config['list']
tenant_config_add = _tenant_config['add']
tenant_config_edit = _tenant_config['edit']
tenant_config_delete = _tenant_config['delete']

# ===== Admin Telemetry =====
_admin_telemetry = make_crud_views(
    model_class=AdminTelemetry,
    display_name='Admin Telemetry',
    fields=[
        {'name': 'metric_name', 'type': 'str', 'required': True, 'label': 'Metric Name'},
        {'name': 'metric_value', 'type': 'float', 'required': True, 'label': 'Metric Value'},
    ],
    list_url_name='admin_telemetry_list',
    add_url_name='admin_telemetry_add',
    edit_url_name='admin_telemetry_edit',
    order_by='-recorded_at',
)
admin_telemetry_list = _admin_telemetry['list']
admin_telemetry_add = _admin_telemetry['add']
admin_telemetry_edit = _admin_telemetry['edit']
admin_telemetry_delete = _admin_telemetry['delete']

# ===== API Rate Limits =====
_api_rate_limit = make_crud_views(
    model_class=APIRateLimitConfig,
    display_name='API Rate Limit',
    fields=[
        {'name': 'endpoint', 'type': 'str', 'required': True, 'label': 'Endpoint'},
        {'name': 'max_requests_per_minute', 'type': 'int', 'default': 60, 'label': 'Max/Minute'},
        {'name': 'max_requests_per_hour', 'type': 'int', 'default': 1000, 'label': 'Max/Hour'},
        {'name': 'is_active', 'type': 'bool', 'default': True, 'label': 'Active'},
    ],
    list_url_name='api_rate_limit_list',
    add_url_name='api_rate_limit_add',
    edit_url_name='api_rate_limit_edit',
    order_by='endpoint',
)
api_rate_limit_list = _api_rate_limit['list']
api_rate_limit_add = _api_rate_limit['add']
api_rate_limit_edit = _api_rate_limit['edit']
api_rate_limit_delete = _api_rate_limit['delete']

# ===== Encryption Keys =====
_encryption_key = make_crud_views(
    model_class=EncryptionKey,
    display_name='Encryption Key',
    fields=[
        {'name': 'key_identifier', 'type': 'str', 'required': True, 'label': 'Key Identifier'},
        {'name': 'public_key', 'type': 'str', 'widget': 'textarea', 'required': True, 'label': 'Public Key'},
        {'name': 'is_active', 'type': 'bool', 'default': True, 'label': 'Active'},
    ],
    list_url_name='encryption_key_list',
    add_url_name='encryption_key_add',
    edit_url_name='encryption_key_edit',
    order_by='-created_at',
)
encryption_key_list = _encryption_key['list']
encryption_key_add = _encryption_key['add']
encryption_key_edit = _encryption_key['edit']
encryption_key_delete = _encryption_key['delete']

# ===== Audit Logs =====
_audit_log = make_crud_views(
    model_class=AuditLog,
    display_name='Audit Log',
    fields=[
        {'name': 'action', 'type': 'str', 'required': True, 'label': 'Action'},
        {'name': 'details', 'type': 'str', 'widget': 'textarea', 'label': 'Details'},
        {'name': 'ip_address', 'type': 'str', 'label': 'IP Address'},
    ],
    list_url_name='audit_log_list',
    add_url_name='audit_log_add',
    edit_url_name='audit_log_edit',
    order_by='-created_at',
)
audit_log_list = _audit_log['list']
audit_log_add = _audit_log['add']
audit_log_edit = _audit_log['edit']
audit_log_delete = _audit_log['delete']

# ===== Anonymized Data =====
_anonymized_data = make_crud_views(
    model_class=AnonymizedDataReport,
    display_name='Anonymized Data Report',
    fields=[
        {'name': 'report_title', 'type': 'str', 'required': True, 'label': 'Report Title'},
        {'name': 'report_type', 'type': 'str', 'choices': AnonymizedDataReport.REPORT_TYPE_CHOICES, 'label': 'Report Type'},
        {'name': 'total_records', 'type': 'int', 'default': 0, 'label': 'Total Records'},
        {'name': 'anonymization_method', 'type': 'str', 'label': 'Anonymization Method'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='anonymized_data_list',
    add_url_name='anonymized_data_add',
    edit_url_name='anonymized_data_edit',
    order_by='-generated_at',
)
anonymized_data_list = _anonymized_data['list']
anonymized_data_add = _anonymized_data['add']
anonymized_data_edit = _anonymized_data['edit']
anonymized_data_delete = _anonymized_data['delete']

# ===== Database Scaling =====
_database_scaling = make_crud_views(
    model_class=DatabaseScalingConfig,
    display_name='Database Scaling',
    fields=[
        {'name': 'config_name', 'type': 'str', 'required': True, 'label': 'Config Name'},
        {'name': 'scaling_type', 'type': 'str', 'choices': DatabaseScalingConfig.SCALING_TYPE_CHOICES, 'label': 'Scaling Type'},
        {'name': 'is_active', 'type': 'bool', 'label': 'Active'},
        {'name': 'max_connections', 'type': 'int', 'default': 100, 'label': 'Max Connections'},
        {'name': 'notes', 'type': 'str', 'widget': 'textarea'},
    ],
    list_url_name='database_scaling_list',
    add_url_name='database_scaling_add',
    edit_url_name='database_scaling_edit',
    order_by='-created_at',
)
database_scaling_list = _database_scaling['list']
database_scaling_add = _database_scaling['add']
database_scaling_edit = _database_scaling['edit']
database_scaling_delete = _database_scaling['delete']

# ===== Backup Config =====
_backup_config = make_crud_views(
    model_class=BackupConfiguration,
    display_name='Backup Configuration',
    fields=[
        {'name': 'backup_name', 'type': 'str', 'required': True, 'label': 'Backup Name'},
        {'name': 'frequency', 'type': 'str', 'choices': BackupConfiguration.FREQUENCY_CHOICES, 'label': 'Frequency'},
        {'name': 'retention_days', 'type': 'int', 'default': 30, 'label': 'Retention (days)'},
        {'name': 'is_active', 'type': 'bool', 'default': True, 'label': 'Active'},
        {'name': 'storage_location', 'type': 'str', 'label': 'Storage Location'},
    ],
    list_url_name='backup_config_list',
    add_url_name='backup_config_add',
    edit_url_name='backup_config_edit',
    order_by='-created_at',
)
backup_config_list = _backup_config['list']
backup_config_add = _backup_config['add']
backup_config_edit = _backup_config['edit']
backup_config_delete = _backup_config['delete']

# ===== Integration Config =====
_integration_config = make_crud_views(
    model_class=IntegrationConfig,
    display_name='Integration Config',
    fields=[
        {'name': 'category', 'type': 'str', 'choices': INTEGRATION_CATEGORIES, 'label': 'Category'},
        {'name': 'feature_type', 'type': 'str', 'choices': INTEGRATION_FEATURE_TYPES, 'label': 'Feature Type'},
        {'name': 'is_enabled', 'type': 'bool', 'label': 'Enabled'},
    ],
    list_url_name='integration_config_list',
    add_url_name='integration_config_add',
    edit_url_name='integration_config_edit',
    order_by='-created_at',
)
integration_config_list = _integration_config['list']
integration_config_add = _integration_config['add']
integration_config_edit = _integration_config['edit']
integration_config_delete = _integration_config['delete']

# ===== Integration Sub-tasks =====
_integration_subtask = make_crud_views(
    model_class=IntegrationSubTask,
    display_name='Integration Sub-task',
    fields=[
        {'name': 'phase', 'type': 'int', 'choices': IntegrationSubTask.PHASE_CHOICES, 'label': 'Phase'},
        {'name': 'sub_task_number', 'type': 'int', 'required': True, 'label': 'Sub-task Number'},
        {'name': 'title', 'type': 'str', 'required': True, 'label': 'Title'},
        {'name': 'category', 'type': 'str', 'choices': INTEGRATION_CATEGORIES, 'label': 'Category'},
        {'name': 'feature_type', 'type': 'str', 'choices': INTEGRATION_FEATURE_TYPES, 'label': 'Feature Type'},
        {'name': 'status', 'type': 'str', 'choices': IntegrationSubTask.STATUS_CHOICES, 'default': 'pending', 'label': 'Status'},
        {'name': 'details', 'type': 'str', 'widget': 'textarea', 'label': 'Details'},
    ],
    list_url_name='integration_subtask_list',
    add_url_name='integration_subtask_add',
    edit_url_name='integration_subtask_edit',
    order_by='phase',
)
integration_subtask_list = _integration_subtask['list']
integration_subtask_add = _integration_subtask['add']
integration_subtask_edit = _integration_subtask['edit']
integration_subtask_delete = _integration_subtask['delete']
