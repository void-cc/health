from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from .models import BloodTest, BloodTestInfo, VitalSign, DataPointAnnotation, DashboardWidget
from datetime import datetime
import csv
import os
import io
import json
import re
from django.http import HttpResponse, JsonResponse

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
        bp_str = f"{vital.systolic_bp}/{vital.diastolic_bp} mmHg" if vital.systolic_bp and vital.diastolic_bp else ""
        hr_str = f"{vital.heart_rate} bpm" if vital.heart_rate else ""
        weight_str = f"{vital.weight} kg" if vital.weight else ""

        details = [val for val in [weight_str, hr_str, bp_str] if val]

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


def vitals(request):
    all_vitals = VitalSign.objects.all().order_by('-date')
    return render(request, 'vitals.html', {'vitals': all_vitals})

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

def delete_test(request, test_id):
    if request.method == 'POST':
        test = get_object_or_404(BloodTest, id=test_id)
        test.delete()
        messages.success(request, 'Blood test deleted successfully!')
    return redirect('index')

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

def add_vitals(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        weight = request.POST.get('weight')
        heart_rate = request.POST.get('heart_rate')
        systolic_bp = request.POST.get('systolic_bp')
        diastolic_bp = request.POST.get('diastolic_bp')

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
                diastolic_bp=int(diastolic_bp) if diastolic_bp else None
            )
            messages.success(request, 'Vital signs added successfully!')
            return redirect('vitals')
        except Exception as e:
            messages.error(request, 'Error adding vital signs. Please try again.')
            return redirect('add_vitals')

    return render(request, 'add_vitals.html', {'date': datetime.now().strftime('%Y-%m-%d')})

def edit_vitals(request, vital_id):
    vital = get_object_or_404(VitalSign, id=vital_id)

    if request.method == 'POST':
        date_str = request.POST.get('date')
        weight = request.POST.get('weight')
        heart_rate = request.POST.get('heart_rate')
        systolic_bp = request.POST.get('systolic_bp')
        diastolic_bp = request.POST.get('diastolic_bp')

        try:
            vital.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            vital.weight = float(weight) if weight else None
            vital.heart_rate = int(heart_rate) if heart_rate else None
            vital.systolic_bp = int(systolic_bp) if systolic_bp else None
            vital.diastolic_bp = int(diastolic_bp) if diastolic_bp else None
            vital.save()

            messages.success(request, 'Vital signs updated successfully!')
            return redirect('vitals')
        except Exception as e:
            messages.error(request, 'Error updating vital signs. Please try again.')
            return redirect('edit_vitals', vital_id=vital.id)

    return render(request, 'edit_vitals.html', {'vital': vital})

def delete_vitals(request, vital_id):
    if request.method == 'POST':
        vital = get_object_or_404(VitalSign, id=vital_id)
        vital.delete()
        messages.success(request, 'Vital sign deleted successfully!')
    return redirect('vitals')

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

def comparative_bar_charts(request):
    tests = BloodTest.objects.all().order_by('-date')
    latest_tests = {}
    for test in tests:
        if test.test_name not in latest_tests:
            if test.normal_min is not None and test.normal_max is not None:
                latest_tests[test.test_name] = test

    return render(request, 'comparative_bar_charts.html', {'latest_tests': latest_tests})

def vitals_charts(request):
    vitals = VitalSign.objects.all().order_by('date')
    weight_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.weight} for v in vitals if v.weight is not None]
    hr_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.heart_rate} for v in vitals if v.heart_rate is not None]
    sys_bp_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.systolic_bp} for v in vitals if v.systolic_bp is not None]
    dia_bp_data = [{'x': v.date.strftime('%Y-%m-%d'), 'y': v.diastolic_bp} for v in vitals if v.diastolic_bp is not None]

    return render(request, 'vitals_charts.html', {
        'weight_data': weight_data,
        'hr_data': hr_data,
        'sys_bp_data': sys_bp_data,
        'dia_bp_data': dia_bp_data
    })

import pdfplumber
import pdf2image
import pytesseract
from thefuzz import process, fuzz

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
        bp_str = f"{vital.systolic_bp}/{vital.diastolic_bp}" if vital.systolic_bp and vital.diastolic_bp else ""
        hr_str = f"{vital.heart_rate} bpm" if vital.heart_rate else ""
        weight_str = f"{vital.weight} kg" if vital.weight else ""

        details = [val for val in [weight_str, hr_str, bp_str] if val]

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


# --- Data Point Annotation views ---

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

    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', reverse('index')))
    return redirect(next_url)


def delete_annotation(request, annotation_id):
    if request.method == 'POST':
        annotation = get_object_or_404(DataPointAnnotation, id=annotation_id)
        annotation.delete()
        messages.success(request, 'Annotation deleted successfully!')
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', reverse('index')))
    return redirect(next_url)


# --- Bulk Data Editing Interface ---

def bulk_edit(request):
    if request.method == 'POST':
        updated = 0
        deleted_ids = request.POST.getlist('delete_ids')

        if deleted_ids:
            BloodTest.objects.filter(id__in=deleted_ids).delete()

        test_ids = request.POST.getlist('test_ids')
        for test_id in test_ids:
            if test_id in deleted_ids:
                continue
            try:
                test = BloodTest.objects.get(id=int(test_id))
                new_value = request.POST.get(f'value_{test_id}')
                new_date = request.POST.get(f'date_{test_id}')
                if new_value is not None and new_date:
                    test.value = float(new_value)
                    test.date = datetime.strptime(new_date, '%Y-%m-%d').date()
                    test.save()
                    updated += 1
            except (BloodTest.DoesNotExist, ValueError, TypeError):
                continue

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


def customize_dashboard(request):
    widgets = _get_dashboard_widgets()
    return render(request, 'customize_dashboard.html', {'widgets': widgets})


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
