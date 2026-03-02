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
from django.utils.http import url_has_allowed_host_and_scheme
from datetime import datetime
import csv
import os
import io
import json
import re
from django.http import HttpResponse, JsonResponse
from django.db.models import Q as models_Q

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
    return render(request, 'body_composition_list.html', {'entries': entries})

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
    return render(request, 'hydration_list.html', {'entries': entries})

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

@login_required
def pain_list(request):
    entries = PainLog.objects.all().order_by('-date')
    return render(request, 'pain_list.html', {'entries': entries, 'body_regions': BODY_REGIONS})

@login_required
def pain_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('pain_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            PainLog.objects.create(
                date=date,
                body_region=request.POST.get('body_region'),
                pain_level=int(request.POST.get('pain_level', 1)),
                description=request.POST.get('description', ''),
            )
            messages.success(request, 'Pain log added!')
            return redirect('pain_list')
        except Exception:
            messages.error(request, 'Error adding pain log.')
            return redirect('pain_add')
    return render(request, 'pain_form.html', {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'body_regions': BODY_REGIONS,
        'editing': False,
    })

@login_required
def pain_edit(request, pk):
    entry = get_object_or_404(PainLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.body_region = request.POST.get('body_region')
            entry.pain_level = int(request.POST.get('pain_level', 1))
            entry.description = request.POST.get('description', '')
            entry.save()
            messages.success(request, 'Pain log updated!')
            return redirect('pain_list')
        except Exception:
            messages.error(request, 'Error updating pain log.')
            return redirect('pain_edit', pk=pk)
    return render(request, 'pain_form.html', {
        'entry': entry,
        'body_regions': BODY_REGIONS,
        'editing': True,
    })

@login_required
def pain_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(PainLog, id=pk).delete()
        messages.success(request, 'Pain log deleted!')
    return redirect('pain_list')


# ===== Phase 2: Resting Metabolic Rate =====

@login_required
def rmr_list(request):
    entries = RestingMetabolicRate.objects.all().order_by('-date')
    return render(request, 'rmr_list.html', {'entries': entries})

@login_required
def rmr_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('rmr_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            RestingMetabolicRate.objects.create(
                date=date,
                age=int(request.POST.get('age', 0)),
                weight_kg=float(request.POST.get('weight_kg', 0)),
                height_cm=float(request.POST.get('height_cm', 0)),
                gender=request.POST.get('gender', 'M'),
                formula=request.POST.get('formula', 'mifflin'),
            )
            messages.success(request, 'RMR entry added!')
            return redirect('rmr_list')
        except Exception:
            messages.error(request, 'Error adding RMR entry.')
            return redirect('rmr_add')
    return render(request, 'rmr_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def rmr_edit(request, pk):
    entry = get_object_or_404(RestingMetabolicRate, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.age = int(request.POST.get('age', 0))
            entry.weight_kg = float(request.POST.get('weight_kg', 0))
            entry.height_cm = float(request.POST.get('height_cm', 0))
            entry.gender = request.POST.get('gender', 'M')
            entry.formula = request.POST.get('formula', 'mifflin')
            entry.save()
            messages.success(request, 'RMR entry updated!')
            return redirect('rmr_list')
        except Exception:
            messages.error(request, 'Error updating RMR entry.')
            return redirect('rmr_edit', pk=pk)
    return render(request, 'rmr_form.html', {'entry': entry, 'editing': True})

@login_required
def rmr_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(RestingMetabolicRate, id=pk).delete()
        messages.success(request, 'RMR entry deleted!')
    return redirect('rmr_list')


# ===== Phase 2: Orthostatic Tracking =====

@login_required
def orthostatic_list(request):
    entries = OrthostaticReading.objects.all().order_by('-date')
    return render(request, 'orthostatic_list.html', {'entries': entries})

@login_required
def orthostatic_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('orthostatic_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            OrthostaticReading.objects.create(
                date=date,
                supine_hr=int(request.POST.get('supine_hr')) if request.POST.get('supine_hr') else None,
                standing_hr=int(request.POST.get('standing_hr')) if request.POST.get('standing_hr') else None,
                supine_systolic=int(request.POST.get('supine_systolic')) if request.POST.get('supine_systolic') else None,
                supine_diastolic=int(request.POST.get('supine_diastolic')) if request.POST.get('supine_diastolic') else None,
                standing_systolic=int(request.POST.get('standing_systolic')) if request.POST.get('standing_systolic') else None,
                standing_diastolic=int(request.POST.get('standing_diastolic')) if request.POST.get('standing_diastolic') else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Orthostatic reading added!')
            return redirect('orthostatic_list')
        except Exception:
            messages.error(request, 'Error adding orthostatic reading.')
            return redirect('orthostatic_add')
    return render(request, 'orthostatic_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def orthostatic_edit(request, pk):
    entry = get_object_or_404(OrthostaticReading, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.supine_hr = int(request.POST.get('supine_hr')) if request.POST.get('supine_hr') else None
            entry.standing_hr = int(request.POST.get('standing_hr')) if request.POST.get('standing_hr') else None
            entry.supine_systolic = int(request.POST.get('supine_systolic')) if request.POST.get('supine_systolic') else None
            entry.supine_diastolic = int(request.POST.get('supine_diastolic')) if request.POST.get('supine_diastolic') else None
            entry.standing_systolic = int(request.POST.get('standing_systolic')) if request.POST.get('standing_systolic') else None
            entry.standing_diastolic = int(request.POST.get('standing_diastolic')) if request.POST.get('standing_diastolic') else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Orthostatic reading updated!')
            return redirect('orthostatic_list')
        except Exception:
            messages.error(request, 'Error updating orthostatic reading.')
            return redirect('orthostatic_edit', pk=pk)
    return render(request, 'orthostatic_form.html', {'entry': entry, 'editing': True})

@login_required
def orthostatic_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(OrthostaticReading, id=pk).delete()
        messages.success(request, 'Orthostatic reading deleted!')
    return redirect('orthostatic_list')


# ===== Phase 2: Reproductive Health =====

@login_required
def reproductive_list(request):
    entries = ReproductiveHealthLog.objects.all().order_by('-date')
    return render(request, 'reproductive_list.html', {'entries': entries})

@login_required
def reproductive_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('reproductive_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            ReproductiveHealthLog.objects.create(
                date=date,
                cycle_day=int(request.POST.get('cycle_day')) if request.POST.get('cycle_day') else None,
                phase=request.POST.get('phase', ''),
                flow_intensity=int(request.POST.get('flow_intensity')) if request.POST.get('flow_intensity') else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Reproductive health entry added!')
            return redirect('reproductive_list')
        except Exception:
            messages.error(request, 'Error adding entry.')
            return redirect('reproductive_add')
    return render(request, 'reproductive_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def reproductive_edit(request, pk):
    entry = get_object_or_404(ReproductiveHealthLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.cycle_day = int(request.POST.get('cycle_day')) if request.POST.get('cycle_day') else None
            entry.phase = request.POST.get('phase', '')
            entry.flow_intensity = int(request.POST.get('flow_intensity')) if request.POST.get('flow_intensity') else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Reproductive health entry updated!')
            return redirect('reproductive_list')
        except Exception:
            messages.error(request, 'Error updating entry.')
            return redirect('reproductive_edit', pk=pk)
    return render(request, 'reproductive_form.html', {'entry': entry, 'editing': True})

@login_required
def reproductive_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(ReproductiveHealthLog, id=pk).delete()
        messages.success(request, 'Reproductive health entry deleted!')
    return redirect('reproductive_list')


# ===== Phase 2: Symptom Journaling =====

@login_required
def symptom_list(request):
    entries = SymptomJournal.objects.all().order_by('-date')
    return render(request, 'symptom_list.html', {'entries': entries})

@login_required
def symptom_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        symptom = request.POST.get('symptom')
        if not date_str or not symptom:
            messages.error(request, 'Date and symptom are required.')
            return redirect('symptom_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            SymptomJournal.objects.create(
                date=date,
                symptom=symptom,
                severity=int(request.POST.get('severity', 1)),
                duration=request.POST.get('duration', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Symptom journal entry added!')
            return redirect('symptom_list')
        except Exception:
            messages.error(request, 'Error adding symptom entry.')
            return redirect('symptom_add')
    return render(request, 'symptom_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def symptom_edit(request, pk):
    entry = get_object_or_404(SymptomJournal, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.symptom = request.POST.get('symptom', '')
            entry.severity = int(request.POST.get('severity', 1))
            entry.duration = request.POST.get('duration', '')
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Symptom journal entry updated!')
            return redirect('symptom_list')
        except Exception:
            messages.error(request, 'Error updating symptom entry.')
            return redirect('symptom_edit', pk=pk)
    return render(request, 'symptom_form.html', {'entry': entry, 'editing': True})

@login_required
def symptom_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(SymptomJournal, id=pk).delete()
        messages.success(request, 'Symptom journal entry deleted!')
    return redirect('symptom_list')


# ===== Phase 2: Metabolic Monitoring =====

@login_required
def metabolic_list(request):
    entries = MetabolicLog.objects.all().order_by('-date')
    return render(request, 'metabolic_list.html', {'entries': entries})

@login_required
def metabolic_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('metabolic_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            MetabolicLog.objects.create(
                date=date,
                blood_glucose=float(request.POST.get('blood_glucose')) if request.POST.get('blood_glucose') else None,
                insulin_level=float(request.POST.get('insulin_level')) if request.POST.get('insulin_level') else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Metabolic log added!')
            return redirect('metabolic_list')
        except Exception:
            messages.error(request, 'Error adding metabolic log.')
            return redirect('metabolic_add')
    return render(request, 'metabolic_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def metabolic_edit(request, pk):
    entry = get_object_or_404(MetabolicLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.blood_glucose = float(request.POST.get('blood_glucose')) if request.POST.get('blood_glucose') else None
            entry.insulin_level = float(request.POST.get('insulin_level')) if request.POST.get('insulin_level') else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Metabolic log updated!')
            return redirect('metabolic_list')
        except Exception:
            messages.error(request, 'Error updating metabolic log.')
            return redirect('metabolic_edit', pk=pk)
    return render(request, 'metabolic_form.html', {'entry': entry, 'editing': True})

@login_required
def metabolic_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(MetabolicLog, id=pk).delete()
        messages.success(request, 'Metabolic log deleted!')
    return redirect('metabolic_list')


# ===== Phase 2: Ketone Level Tracking =====

@login_required
def ketone_list(request):
    entries = KetoneLog.objects.all().order_by('-date')
    return render(request, 'ketone_list.html', {'entries': entries})

@login_required
def ketone_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('ketone_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            KetoneLog.objects.create(
                date=date,
                value=float(request.POST.get('value', 0)),
                measurement_type=request.POST.get('measurement_type', 'blood'),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Ketone log added!')
            return redirect('ketone_list')
        except Exception:
            messages.error(request, 'Error adding ketone log.')
            return redirect('ketone_add')
    return render(request, 'ketone_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

@login_required
def ketone_edit(request, pk):
    entry = get_object_or_404(KetoneLog, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            entry.value = float(request.POST.get('value', 0))
            entry.measurement_type = request.POST.get('measurement_type', 'blood')
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Ketone log updated!')
            return redirect('ketone_list')
        except Exception:
            messages.error(request, 'Error updating ketone log.')
            return redirect('ketone_edit', pk=pk)
    return render(request, 'ketone_form.html', {'entry': entry, 'editing': True})

@login_required
def ketone_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(KetoneLog, id=pk).delete()
        messages.success(request, 'Ketone log deleted!')
    return redirect('ketone_list')
# --- Data Point Annotation views ---

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
    return render(request, 'wearable_device_list.html', {'entries': entries})

def wearable_device_add(request):
    if request.method == 'POST':
        try:
            WearableDevice.objects.create(
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

def sync_log_list(request):
    entries = WearableSyncLog.objects.all().order_by('-started_at')
    return render(request, 'sync_log_list.html', {'entries': entries})


# ===== Phase 6: Sleep & Circadian =====

@login_required
def sleep_list(request):
    entries = SleepLog.objects.all().order_by('-date')
    return render(request, 'sleep_list.html', {'entries': entries})

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
    return render(request, 'macro_list.html', {'entries': entries})

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


# ===== Phase 8: Medication Schedule =====

def medication_schedule_list(request):
    entries = MedicationSchedule.objects.all().order_by('-start_date')
    return render(request, 'medication_schedule_list.html', {'entries': entries})

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
    return render(request, 'health_goal_list.html', {'entries': entries})

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
        get_object_or_404(HealthGoal, id=pk).delete()
        messages.success(request, 'Health goal deleted!')
    return redirect('health_goal_list')


# ===== Phase 8: Critical Alert =====

def critical_alert_list(request):
    entries = CriticalAlert.objects.all().order_by('-triggered_at')
    return render(request, 'critical_alert_list.html', {'entries': entries})

def critical_alert_add(request):
    if request.method == 'POST':
        try:
            metric_value = request.POST.get('metric_value', '').strip()
            threshold = request.POST.get('threshold_value', '').strip()
            CriticalAlert.objects.create(
                metric_name=request.POST.get('metric_name', ''),
                metric_value=float(metric_value) if metric_value else None,
                threshold_value=float(threshold) if threshold else None,
                alert_level=request.POST.get('alert_level', ''),
                message=request.POST.get('message', ''),
                acknowledged=request.POST.get('acknowledged') == 'on',
            )
            messages.success(request, 'Critical alert added!')
            return redirect('critical_alert_list')
        except Exception:
            messages.error(request, 'Error adding critical alert.')
            return redirect('critical_alert_add')
    return render(request, 'critical_alert_form.html', {'editing': False})

def critical_alert_edit(request, pk):
    entry = get_object_or_404(CriticalAlert, id=pk)
    if request.method == 'POST':
        try:
            metric_value = request.POST.get('metric_value', '').strip()
            threshold = request.POST.get('threshold_value', '').strip()
            entry.metric_name = request.POST.get('metric_name', '')
            entry.metric_value = float(metric_value) if metric_value else None
            entry.threshold_value = float(threshold) if threshold else None
            entry.alert_level = request.POST.get('alert_level', '')
            entry.message = request.POST.get('message', '')
            entry.acknowledged = request.POST.get('acknowledged') == 'on'
            entry.save()
            messages.success(request, 'Critical alert updated!')
            return redirect('critical_alert_list')
        except Exception:
            messages.error(request, 'Error updating critical alert.')
            return redirect('critical_alert_edit', pk=pk)
    return render(request, 'critical_alert_form.html', {'entry': entry, 'editing': True})

def critical_alert_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(CriticalAlert, id=pk).delete()
        messages.success(request, 'Critical alert deleted!')
    return redirect('critical_alert_list')


# ===== Phase 8: Health Report =====

def health_report_list(request):
    entries = HealthReport.objects.all().order_by('-generated_at')
    return render(request, 'health_report_list.html', {'entries': entries})

def health_report_add(request):
    if request.method == 'POST':
        try:
            period_start_str = request.POST.get('period_start', '').strip()
            period_end_str = request.POST.get('period_end', '').strip()
            HealthReport.objects.create(
                report_type=request.POST.get('report_type', ''),
                title=request.POST.get('title', ''),
                content=request.POST.get('content', ''),
                period_start=datetime.strptime(period_start_str, '%Y-%m-%d').date() if period_start_str else None,
                period_end=datetime.strptime(period_end_str, '%Y-%m-%d').date() if period_end_str else None,
            )
            messages.success(request, 'Health report added!')
            return redirect('health_report_list')
        except Exception:
            messages.error(request, 'Error adding health report.')
            return redirect('health_report_add')
    return render(request, 'health_report_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

def health_report_edit(request, pk):
    entry = get_object_or_404(HealthReport, id=pk)
    if request.method == 'POST':
        try:
            period_start_str = request.POST.get('period_start', '').strip()
            period_end_str = request.POST.get('period_end', '').strip()
            entry.report_type = request.POST.get('report_type', '')
            entry.title = request.POST.get('title', '')
            entry.content = request.POST.get('content', '')
            entry.period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date() if period_start_str else None
            entry.period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date() if period_end_str else None
            entry.save()
            messages.success(request, 'Health report updated!')
            return redirect('health_report_list')
        except Exception:
            messages.error(request, 'Error updating health report.')
            return redirect('health_report_edit', pk=pk)
    return render(request, 'health_report_form.html', {'entry': entry, 'editing': True})

def health_report_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(HealthReport, id=pk).delete()
        messages.success(request, 'Health report deleted!')
    return redirect('health_report_list')


# ===== Phase 8: Biological Age Calculation =====

def biological_age_list(request):
    entries = BiologicalAgeCalculation.objects.all().order_by('-date')
    return render(request, 'biological_age_list.html', {'entries': entries})

def biological_age_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Please select a date.')
            return redirect('biological_age_add')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        try:
            chrono = request.POST.get('chronological_age', '').strip()
            bio = request.POST.get('biological_age', '').strip()
            BiologicalAgeCalculation.objects.create(
                date=date,
                chronological_age=float(chrono) if chrono else None,
                biological_age=float(bio) if bio else None,
                method=request.POST.get('method', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Biological age calculation added!')
            return redirect('biological_age_list')
        except Exception:
            messages.error(request, 'Error adding biological age calculation.')
            return redirect('biological_age_add')
    return render(request, 'biological_age_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

def biological_age_edit(request, pk):
    entry = get_object_or_404(BiologicalAgeCalculation, id=pk)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            chrono = request.POST.get('chronological_age', '').strip()
            bio = request.POST.get('biological_age', '').strip()
            entry.chronological_age = float(chrono) if chrono else None
            entry.biological_age = float(bio) if bio else None
            entry.method = request.POST.get('method', '')
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Biological age calculation updated!')
            return redirect('biological_age_list')
        except Exception:
            messages.error(request, 'Error updating biological age calculation.')
            return redirect('biological_age_edit', pk=pk)
    return render(request, 'biological_age_form.html', {'entry': entry, 'editing': True})

def biological_age_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(BiologicalAgeCalculation, id=pk).delete()
        messages.success(request, 'Biological age calculation deleted!')
    return redirect('biological_age_list')


# ===== Phase 8: Predictive Biomarker =====

def predictive_biomarker_list(request):
    entries = PredictiveBiomarker.objects.all().order_by('-generated_at')
    return render(request, 'predictive_biomarker_list.html', {'entries': entries})

def predictive_biomarker_add(request):
    if request.method == 'POST':
        try:
            predicted = request.POST.get('predicted_value', '').strip()
            confidence = request.POST.get('confidence_percent', '').strip()
            pred_date_str = request.POST.get('prediction_date', '').strip()
            PredictiveBiomarker.objects.create(
                biomarker_name=request.POST.get('biomarker_name', ''),
                predicted_value=float(predicted) if predicted else None,
                confidence_percent=float(confidence) if confidence else None,
                prediction_date=datetime.strptime(pred_date_str, '%Y-%m-%d').date() if pred_date_str else None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Predictive biomarker added!')
            return redirect('predictive_biomarker_list')
        except Exception:
            messages.error(request, 'Error adding predictive biomarker.')
            return redirect('predictive_biomarker_add')
    return render(request, 'predictive_biomarker_form.html', {'date': datetime.now().strftime('%Y-%m-%d'), 'editing': False})

def predictive_biomarker_edit(request, pk):
    entry = get_object_or_404(PredictiveBiomarker, id=pk)
    if request.method == 'POST':
        try:
            predicted = request.POST.get('predicted_value', '').strip()
            confidence = request.POST.get('confidence_percent', '').strip()
            pred_date_str = request.POST.get('prediction_date', '').strip()
            entry.biomarker_name = request.POST.get('biomarker_name', '')
            entry.predicted_value = float(predicted) if predicted else None
            entry.confidence_percent = float(confidence) if confidence else None
            entry.prediction_date = datetime.strptime(pred_date_str, '%Y-%m-%d').date() if pred_date_str else None
            entry.notes = request.POST.get('notes', '')
            entry.save()
            messages.success(request, 'Predictive biomarker updated!')
            return redirect('predictive_biomarker_list')
        except Exception:
            messages.error(request, 'Error updating predictive biomarker.')
            return redirect('predictive_biomarker_edit', pk=pk)
    return render(request, 'predictive_biomarker_form.html', {'entry': entry, 'editing': True})

def predictive_biomarker_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(PredictiveBiomarker, id=pk).delete()
        messages.success(request, 'Predictive biomarker deleted!')
    return redirect('predictive_biomarker_list')


# ===== Phase 9: Secure Viewing Link =====

def secure_viewing_link_list(request):
    entries = SecureViewingLink.objects.all().order_by('-created_at')
    return render(request, 'secure_viewing_link_list.html', {'entries': entries})

def secure_viewing_link_add(request):
    if request.method == 'POST':
        try:
            access_count = request.POST.get('access_count', '').strip()
            SecureViewingLink.objects.create(
                token=request.POST.get('token', ''),
                data_types=request.POST.get('data_types', ''),
                expires_at=request.POST.get('expires_at', '') or None,
                is_active=request.POST.get('is_active') == 'on',
                access_count=int(access_count) if access_count else 0,
            )
            messages.success(request, 'Secure viewing link added!')
            return redirect('secure_viewing_link_list')
        except Exception:
            messages.error(request, 'Error adding secure viewing link.')
            return redirect('secure_viewing_link_add')
    return render(request, 'secure_viewing_link_form.html', {'editing': False})

def secure_viewing_link_edit(request, pk):
    entry = get_object_or_404(SecureViewingLink, id=pk)
    if request.method == 'POST':
        try:
            access_count = request.POST.get('access_count', '').strip()
            entry.token = request.POST.get('token', '')
            entry.data_types = request.POST.get('data_types', '')
            entry.expires_at = request.POST.get('expires_at', '') or None
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.access_count = int(access_count) if access_count else 0
            entry.save()
            messages.success(request, 'Secure viewing link updated!')
            return redirect('secure_viewing_link_list')
        except Exception:
            messages.error(request, 'Error updating secure viewing link.')
            return redirect('secure_viewing_link_edit', pk=pk)
    return render(request, 'secure_viewing_link_form.html', {'entry': entry, 'editing': True})

def secure_viewing_link_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(SecureViewingLink, id=pk).delete()
        messages.success(request, 'Secure viewing link deleted!')
    return redirect('secure_viewing_link_list')


# ===== Phase 9: Practitioner Access =====

def practitioner_access_list(request):
    entries = PractitionerAccess.objects.all().order_by('-granted_at')
    return render(request, 'practitioner_access_list.html', {'entries': entries})

def practitioner_access_add(request):
    if request.method == 'POST':
        try:
            PractitionerAccess.objects.create(
                practitioner_name=request.POST.get('practitioner_name', ''),
                practitioner_email=request.POST.get('practitioner_email', ''),
                specialty=request.POST.get('specialty', ''),
                access_status=request.POST.get('access_status', ''),
                expires_at=request.POST.get('expires_at', '') or None,
            )
            messages.success(request, 'Practitioner access added!')
            return redirect('practitioner_access_list')
        except Exception:
            messages.error(request, 'Error adding practitioner access.')
            return redirect('practitioner_access_add')
    return render(request, 'practitioner_access_form.html', {'editing': False})

def practitioner_access_edit(request, pk):
    entry = get_object_or_404(PractitionerAccess, id=pk)
    if request.method == 'POST':
        try:
            entry.practitioner_name = request.POST.get('practitioner_name', '')
            entry.practitioner_email = request.POST.get('practitioner_email', '')
            entry.specialty = request.POST.get('specialty', '')
            entry.access_status = request.POST.get('access_status', '')
            entry.expires_at = request.POST.get('expires_at', '') or None
            entry.save()
            messages.success(request, 'Practitioner access updated!')
            return redirect('practitioner_access_list')
        except Exception:
            messages.error(request, 'Error updating practitioner access.')
            return redirect('practitioner_access_edit', pk=pk)
    return render(request, 'practitioner_access_form.html', {'entry': entry, 'editing': True})

def practitioner_access_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(PractitionerAccess, id=pk).delete()
        messages.success(request, 'Practitioner access deleted!')
    return redirect('practitioner_access_list')


# ===== Phase 9: Intake Summary =====

def intake_summary_list(request):
    entries = IntakeSummary.objects.all().order_by('-generated_at')
    return render(request, 'intake_summary_list.html', {'entries': entries})

def intake_summary_add(request):
    if request.method == 'POST':
        try:
            IntakeSummary.objects.create(
                title=request.POST.get('title', ''),
                summary_text=request.POST.get('summary_text', ''),
                conditions=request.POST.get('conditions', ''),
                medications=request.POST.get('medications', ''),
                allergies=request.POST.get('allergies', ''),
            )
            messages.success(request, 'Intake summary added!')
            return redirect('intake_summary_list')
        except Exception:
            messages.error(request, 'Error adding intake summary.')
            return redirect('intake_summary_add')
    return render(request, 'intake_summary_form.html', {'editing': False})

def intake_summary_edit(request, pk):
    entry = get_object_or_404(IntakeSummary, id=pk)
    if request.method == 'POST':
        try:
            entry.title = request.POST.get('title', '')
            entry.summary_text = request.POST.get('summary_text', '')
            entry.conditions = request.POST.get('conditions', '')
            entry.medications = request.POST.get('medications', '')
            entry.allergies = request.POST.get('allergies', '')
            entry.save()
            messages.success(request, 'Intake summary updated!')
            return redirect('intake_summary_list')
        except Exception:
            messages.error(request, 'Error updating intake summary.')
            return redirect('intake_summary_edit', pk=pk)
    return render(request, 'intake_summary_form.html', {'entry': entry, 'editing': True})

def intake_summary_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(IntakeSummary, id=pk).delete()
        messages.success(request, 'Intake summary deleted!')
    return redirect('intake_summary_list')


# ===== Phase 9: Data Export Request =====

def data_export_list(request):
    entries = DataExportRequest.objects.all().order_by('-requested_at')
    return render(request, 'data_export_list.html', {'entries': entries})

def data_export_add(request):
    if request.method == 'POST':
        try:
            DataExportRequest.objects.create(
                export_format=request.POST.get('export_format', ''),
                status=request.POST.get('status', ''),
                file_path=request.POST.get('file_path', ''),
            )
            messages.success(request, 'Data export request added!')
            return redirect('data_export_list')
        except Exception:
            messages.error(request, 'Error adding data export request.')
            return redirect('data_export_add')
    return render(request, 'data_export_form.html', {'editing': False})

def data_export_edit(request, pk):
    entry = get_object_or_404(DataExportRequest, id=pk)
    if request.method == 'POST':
        try:
            entry.export_format = request.POST.get('export_format', '')
            entry.status = request.POST.get('status', '')
            entry.file_path = request.POST.get('file_path', '')
            entry.save()
            messages.success(request, 'Data export request updated!')
            return redirect('data_export_list')
        except Exception:
            messages.error(request, 'Error updating data export request.')
            return redirect('data_export_edit', pk=pk)
    return render(request, 'data_export_form.html', {'entry': entry, 'editing': True})

def data_export_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(DataExportRequest, id=pk).delete()
        messages.success(request, 'Data export request deleted!')
    return redirect('data_export_list')


# ===== Phase 9: Stakeholder Email =====

def stakeholder_email_list(request):
    entries = StakeholderEmail.objects.all().order_by('-created_at')
    return render(request, 'stakeholder_email_list.html', {'entries': entries})

def stakeholder_email_add(request):
    if request.method == 'POST':
        try:
            StakeholderEmail.objects.create(
                recipient_name=request.POST.get('recipient_name', ''),
                recipient_email=request.POST.get('recipient_email', ''),
                frequency=request.POST.get('frequency', ''),
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'Stakeholder email added!')
            return redirect('stakeholder_email_list')
        except Exception:
            messages.error(request, 'Error adding stakeholder email.')
            return redirect('stakeholder_email_add')
    return render(request, 'stakeholder_email_form.html', {'editing': False})

def stakeholder_email_edit(request, pk):
    entry = get_object_or_404(StakeholderEmail, id=pk)
    if request.method == 'POST':
        try:
            entry.recipient_name = request.POST.get('recipient_name', '')
            entry.recipient_email = request.POST.get('recipient_email', '')
            entry.frequency = request.POST.get('frequency', '')
            entry.is_active = request.POST.get('is_active') == 'on'
            entry.save()
            messages.success(request, 'Stakeholder email updated!')
            return redirect('stakeholder_email_list')
        except Exception:
            messages.error(request, 'Error updating stakeholder email.')
            return redirect('stakeholder_email_edit', pk=pk)
    return render(request, 'stakeholder_email_form.html', {'entry': entry, 'editing': True})

def stakeholder_email_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(StakeholderEmail, id=pk).delete()
        messages.success(request, 'Stakeholder email deleted!')
    return redirect('stakeholder_email_list')


# ===== Phase 10-12: Integration Config =====

def integration_config_list(request):
    entries = IntegrationConfig.objects.all().order_by('-created_at')
    return render(request, 'integration_config_list.html', {'entries': entries})

def integration_config_add(request):
    if request.method == 'POST':
        try:
            IntegrationConfig.objects.create(
                category=request.POST.get('category', ''),
                feature_type=request.POST.get('feature_type', ''),
                is_enabled=request.POST.get('is_enabled') == 'on',
                configuration=request.POST.get('configuration', ''),
            )
            messages.success(request, 'Integration config added!')
            return redirect('integration_config_list')
        except Exception:
            messages.error(request, 'Error adding integration config.')
            return redirect('integration_config_add')
    return render(request, 'integration_config_form.html', {
        'editing': False,
        'categories': INTEGRATION_CATEGORIES,
        'feature_types': INTEGRATION_FEATURE_TYPES,
    })

def integration_config_edit(request, pk):
    entry = get_object_or_404(IntegrationConfig, id=pk)
    if request.method == 'POST':
        try:
            entry.category = request.POST.get('category', '')
            entry.feature_type = request.POST.get('feature_type', '')
            entry.is_enabled = request.POST.get('is_enabled') == 'on'
            entry.configuration = request.POST.get('configuration', '')
            entry.save()
            messages.success(request, 'Integration config updated!')
            return redirect('integration_config_list')
        except Exception:
            messages.error(request, 'Error updating integration config.')
            return redirect('integration_config_edit', pk=pk)
    return render(request, 'integration_config_form.html', {
        'entry': entry,
        'editing': True,
        'categories': INTEGRATION_CATEGORIES,
        'feature_types': INTEGRATION_FEATURE_TYPES,
    })

def integration_config_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(IntegrationConfig, id=pk).delete()
        messages.success(request, 'Integration config deleted!')
    return redirect('integration_config_list')


# ===== Phase 10-12: Integration Sub-Task =====

def integration_subtask_list(request):
    entries = IntegrationSubTask.objects.all().order_by('-created_at')
    return render(request, 'integration_subtask_list.html', {'entries': entries})

def integration_subtask_add(request):
    if request.method == 'POST':
        try:
            phase = request.POST.get('phase', '').strip()
            sub_task_number = request.POST.get('sub_task_number', '').strip()
            IntegrationSubTask.objects.create(
                phase=int(phase) if phase else None,
                sub_task_number=int(sub_task_number) if sub_task_number else None,
                title=request.POST.get('title', ''),
                category=request.POST.get('category', ''),
                feature_type=request.POST.get('feature_type', ''),
                status=request.POST.get('status', ''),
                details=request.POST.get('details', ''),
            )
            messages.success(request, 'Integration sub-task added!')
            return redirect('integration_subtask_list')
        except Exception:
            messages.error(request, 'Error adding integration sub-task.')
            return redirect('integration_subtask_add')
    return render(request, 'integration_subtask_form.html', {
        'editing': False,
        'categories': INTEGRATION_CATEGORIES,
        'feature_types': INTEGRATION_FEATURE_TYPES,
    })

def integration_subtask_edit(request, pk):
    entry = get_object_or_404(IntegrationSubTask, id=pk)
    if request.method == 'POST':
        try:
            phase = request.POST.get('phase', '').strip()
            sub_task_number = request.POST.get('sub_task_number', '').strip()
            entry.phase = int(phase) if phase else None
            entry.sub_task_number = int(sub_task_number) if sub_task_number else None
            entry.title = request.POST.get('title', '')
            entry.category = request.POST.get('category', '')
            entry.feature_type = request.POST.get('feature_type', '')
            entry.status = request.POST.get('status', '')
            entry.details = request.POST.get('details', '')
            entry.save()
            messages.success(request, 'Integration sub-task updated!')
            return redirect('integration_subtask_list')
        except Exception:
            messages.error(request, 'Error updating integration sub-task.')
            return redirect('integration_subtask_edit', pk=pk)
    return render(request, 'integration_subtask_form.html', {
        'entry': entry,
        'editing': True,
        'categories': INTEGRATION_CATEGORIES,
        'feature_types': INTEGRATION_FEATURE_TYPES,
    })

def integration_subtask_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(IntegrationSubTask, id=pk).delete()
        messages.success(request, 'Integration sub-task deleted!')
    return redirect('integration_subtask_list')
