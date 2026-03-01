import csv
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, BloodTest, BloodTestInfo, VitalSign
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
import io
from flask import Response

test_url = os.getenv('DATABASE_URL')
print(test_url)


# Configure Database, If not using Heroku, then use SQLite
database_url = os.getenv("DATABASE_URL")
if database_url is None:
    database_url = "sqlite:///blood_tests.db"
else:
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
print(database_url)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configure Database
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
def load_test_info():
    test_info = {}
    with open('blood_tests.csv', mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            test_name = row['test_name']
            unit = row['unit']
            normal_min = row['normal_min']
            normal_max = row['normal_max']
            category = row.get('category', 'Uncategorized')

            # Handle tests without numerical normal ranges
            try:
                normal_min = float(normal_min) if normal_min else None
                normal_max = float(normal_max) if normal_max else None
            except ValueError:
                normal_min = None
                normal_max = None

            test_info[test_name] = {
                'unit': unit,
                'normal_min': normal_min,
                'normal_max': normal_max,
                'category': category
            }
    return test_info


# Initialize TEST_INFO
TEST_INFO = load_test_info()


@app.route('/')
def index():
    tests = BloodTest.query.order_by(BloodTest.date.desc()).all()
    test_types = set(test.test_name for test in tests)

    # Calculate Summary Stats
    total_tests = len(tests)
    out_of_range = sum(1 for test in tests if test.normal_min is not None and test.normal_max is not None and not (test.normal_min <= test.value <= test.normal_max))
    latest_vitals = VitalSign.query.order_by(VitalSign.date.desc()).first()

    # Create a dictionary to store the normal ranges for each test so that
    # we can display them as progress bars in the template. But adjust the
    # length of the progress bar based on the value of the test.
    bars = {}

    # Group tests by category
    tests_by_category = {}
    for test in tests:
        cat = test.category or 'Uncategorized'
        if cat not in tests_by_category:
            tests_by_category[cat] = []
        tests_by_category[cat].append(test)

    for test in tests:
        if test.normal_min is not None and test.normal_max is not None:
            # Prevent division by zero if normal_min == normal_max
            normal_range = test.normal_max - test.normal_min
            if normal_range == 0:
                normal_range = 1.0

            # Establish an absolute scale that comfortably fits the value and the normal range
            abs_min = min(test.normal_min - normal_range, test.value - normal_range * 0.2)
            if abs_min < 0 and test.normal_min >= 0:
                abs_min = 0

            abs_max = max(test.normal_max + normal_range, test.value + normal_range * 0.2)
            total_range = abs_max - abs_min
            if total_range == 0:
                total_range = 1.0

            # Calculate percentages for the THREE zones: Low, Normal, High
            low_width = max(0, ((test.normal_min - abs_min) / total_range) * 100)
            normal_width = max(0, ((test.normal_max - test.normal_min) / total_range) * 100)
            high_width = max(0, ((abs_max - test.normal_max) / total_range) * 100)

            # Ensure widths add up to exactly 100 to avoid wrapping
            total_width = low_width + normal_width + high_width
            if total_width > 0:
                low_width = (low_width / total_width) * 100
                normal_width = (normal_width / total_width) * 100
                high_width = (high_width / total_width) * 100

            # Map value to percentage on this absolute scale
            value_pos = max(0, min(100, ((test.value - abs_min) / total_range) * 100))

            bars[test.id] = {
                'low_width': low_width,
                'normal_width': normal_width,
                'high_width': high_width,
                'value_pos': value_pos,
                'value': test.value,
                'unit': test.unit
            }

    return render_template('index.html', tests=tests, test_types=test_types, bars=bars,
                           total_tests=total_tests, out_of_range=out_of_range,
                           latest_vitals=latest_vitals, tests_by_category=tests_by_category)


@app.route('/chart/<test_name>')
def chart(test_name):
    tests = BloodTest.query.filter_by(test_name=test_name).order_by(BloodTest.date).all()
    dates = [test.date.strftime('%Y-%m-%d') for test in tests]
    values = [test.value for test in tests]
    return render_template('chart.html', dates=dates, values=values, test_name=test_name)

@app.route('/add', methods=['GET', 'POST'])
def add_test():
    if request.method == 'POST':
        date_str = request.form.get('date')
        test_names = request.form.getlist('test_names')

        if not date_str or not test_names:
            flash('Please select a date and at least one blood test.', 'danger')
            return redirect(url_for('add_test'))

        date = datetime.strptime(date_str, '%Y-%m-%d')
        tests_added = 0

        values_dict = request.form.to_dict(flat=False)
        for test_name in test_names:
            value = request.form.get('values[{}]'.format(test_name))
            if not value:
                flash(f'No value provided for {test_name}.', 'warning')
                continue  # Skip if value is missing

            # Convert value to float if applicable
            try:
                value = float(value)
            except ValueError:
                flash(f'Invalid value for {test_name}. Please enter a numeric value.', 'danger')
                continue  # Skip this test

            # Get test info
            test_info = TEST_INFO.get(test_name)
            if not test_info:
                flash(f'Test "{test_name}" not found.', 'danger')
                continue  # Skip invalid test

            # Create new BloodTest entry
            new_test = BloodTest(
                test_name=test_name,
                value=value,
                unit=test_info['unit'],
                date=date,
                normal_min=test_info['normal_min'],
                normal_max=test_info['normal_max'],
                category=test_info.get('category', 'Uncategorized')
            )
            db.session.add(new_test)
            tests_added += 1

        try:
            db.session.commit()
            if tests_added > 0:
                flash(f'{tests_added} blood test(s) added successfully!', 'success')
            else:
                flash('No tests were added. Please provide valid values for the selected tests.', 'warning')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding blood tests. Please try again.', 'danger')
            return redirect(url_for('add_test'))

    else:
        return render_template('add.html', test_info=TEST_INFO, date=datetime.now().strftime('%Y-%m-%d'))


@app.route('/add_test_info', methods=['GET', 'POST'])
def add_test_info():
    if request.method == 'POST':
        test_name = request.form['test_name']
        unit = request.form['unit']
        normal_min = request.form['normal_min']
        normal_max = request.form['normal_max']
        category = request.form.get('category', 'Uncategorized')

        # Validate inputs
        if not test_name or not unit or not normal_min or not normal_max:
            flash('Please fill out all fields.', 'danger')
            return redirect(url_for('add_test_info'))

        # Append the new test to the CSV file
        with open('blood_tests.csv', mode='a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([test_name, unit, normal_min, normal_max, category])

        # Reload TEST_INFO
        global TEST_INFO
        TEST_INFO = load_test_info()

        flash('New blood test added successfully!', 'success')
        return redirect(url_for('add_test'))

    return render_template('add_test_info.html')


@app.route('/delete/<int:test_id>', methods=['POST'])
def delete_test(test_id):
    test = BloodTest.query.get_or_404(test_id)
    try:
        db.session.delete(test)
        db.session.commit()
        flash('Blood test deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting blood test. Please try again.', 'danger')
    return redirect(url_for('index'))


@app.route('/edit/<int:test_id>', methods=['GET', 'POST'])
def edit_test(test_id):
    test = BloodTest.query.get_or_404(test_id)

    if request.method == 'POST':
        # Get updated values from the form
        value = request.form['value']
        date_str = request.form['date']

        try:
            # Update test fields
            test.value = value
            test.date = datetime.strptime(date_str, '%Y-%m-%d')
            db.session.commit()
            flash('Blood test updated successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating blood test. Please try again.', 'danger')
            return redirect(url_for('edit_test', test_id=test.id))
    else:
        return render_template('edit.html', test=test)


@app.route('/vitals')
def vitals():
    all_vitals = VitalSign.query.order_by(VitalSign.date.desc()).all()
    return render_template('vitals.html', vitals=all_vitals)

@app.route('/vitals/add', methods=['GET', 'POST'])
def add_vitals():
    if request.method == 'POST':
        date_str = request.form.get('date')
        weight = request.form.get('weight')
        heart_rate = request.form.get('heart_rate')
        systolic_bp = request.form.get('systolic_bp')
        diastolic_bp = request.form.get('diastolic_bp')

        if not date_str:
            flash('Please select a date.', 'danger')
            return redirect(url_for('add_vitals'))

        date = datetime.strptime(date_str, '%Y-%m-%d')

        try:
            new_vital = VitalSign(
                date=date,
                weight=float(weight) if weight else None,
                heart_rate=int(heart_rate) if heart_rate else None,
                systolic_bp=int(systolic_bp) if systolic_bp else None,
                diastolic_bp=int(diastolic_bp) if diastolic_bp else None
            )
            db.session.add(new_vital)
            db.session.commit()
            flash('Vital signs added successfully!', 'success')
            return redirect(url_for('vitals'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding vital signs. Please try again.', 'danger')
            return redirect(url_for('add_vitals'))
    return render_template('add_vitals.html', date=datetime.now().strftime('%Y-%m-%d'))


@app.route('/vitals/edit/<int:vital_id>', methods=['GET', 'POST'])
def edit_vitals(vital_id):
    vital = VitalSign.query.get_or_404(vital_id)

    if request.method == 'POST':
        date_str = request.form.get('date')
        weight = request.form.get('weight')
        heart_rate = request.form.get('heart_rate')
        systolic_bp = request.form.get('systolic_bp')
        diastolic_bp = request.form.get('diastolic_bp')

        try:
            vital.date = datetime.strptime(date_str, '%Y-%m-%d')
            vital.weight = float(weight) if weight else None
            vital.heart_rate = int(heart_rate) if heart_rate else None
            vital.systolic_bp = int(systolic_bp) if systolic_bp else None
            vital.diastolic_bp = int(diastolic_bp) if diastolic_bp else None

            db.session.commit()
            flash('Vital signs updated successfully!', 'success')
            return redirect(url_for('vitals'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating vital signs. Please try again.', 'danger')
            return redirect(url_for('edit_vitals', vital_id=vital.id))

    return render_template('edit_vitals.html', vital=vital)


@app.route('/vitals/delete/<int:vital_id>', methods=['POST'])
def delete_vitals(vital_id):
    vital = VitalSign.query.get_or_404(vital_id)
    try:
        db.session.delete(vital)
        db.session.commit()
        flash('Vital sign deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting vital sign. Please try again.', 'danger')
    return redirect(url_for('vitals'))


@app.route('/history')
def history():
    tests = BloodTest.query.order_by(BloodTest.date.desc()).all()
    vitals = VitalSign.query.order_by(VitalSign.date.desc()).all()

    # Combine and sort all records by date
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

    return render_template('history.html', history=history_items)


@app.route('/export')
def export_data():
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Date', 'Type', 'Name', 'Value', 'Unit', 'Normal Min', 'Normal Max', 'Status', 'Notes'])

    # Query data
    tests = BloodTest.query.order_by(BloodTest.date.desc()).all()
    vitals = VitalSign.query.order_by(VitalSign.date.desc()).all()

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
            item['normal_min'],
            item['normal_max'],
            item['status'],
            item['notes']
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=medical_history.csv"}
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
