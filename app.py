import csv
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, BloodTest, BloodTestInfo
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configure Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blood_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def load_test_info():
    test_info = {}
    with open('blood_tests.csv', mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            test_name = row['test_name']
            unit = row['unit']
            normal_min = row['normal_min']
            normal_max = row['normal_max']

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
                'normal_max': normal_max
            }
    return test_info


# Initialize TEST_INFO
TEST_INFO = load_test_info()


@app.route('/')
def index():
    tests = BloodTest.query.order_by(BloodTest.date.desc()).all()
    test_types = set(test.test_name for test in tests)
    return render_template('index.html', tests=tests, test_types=test_types)


@app.route('/chart/<test_name>')
def chart(test_name):
    tests = BloodTest.query.filter_by(test_name=test_name).order_by(BloodTest.date).all()
    dates = [test.date.strftime('%Y-%m-%d') for test in tests]
    values = [test.value for test in tests]
    return render_template('chart.html', dates=dates, values=values, test_name=test_name)


@app.route('/add', methods=['GET', 'POST'])
def add_test():
    if request.method == 'POST':
        test_name = request.form['test_name']
        value = float(request.form['value'])
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')

        # Get test info
        test_info = TEST_INFO.get(test_name)
        if not test_info:
            flash('Test not found.', 'danger')
            return redirect(url_for('add_test'))

        new_test = BloodTest(
            test_name=test_name,
            value=value,
            unit=test_info['unit'],
            date=date,
            normal_min=test_info['normal_min'],
            normal_max=test_info['normal_max']
        )

        db.session.add(new_test)
        db.session.commit()
        flash('Blood test added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add.html', test_info=TEST_INFO)


@app.route('/add_test_info', methods=['GET', 'POST'])
def add_test_info():
    if request.method == 'POST':
        test_name = request.form['test_name']
        unit = request.form['unit']
        normal_min = request.form['normal_min']
        normal_max = request.form['normal_max']

        # Validate inputs
        if not test_name or not unit or not normal_min or not normal_max:
            flash('Please fill out all fields.', 'danger')
            return redirect(url_for('add_test_info'))

        # Append the new test to the CSV file
        with open('blood_tests.csv', mode='a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([test_name, unit, normal_min, normal_max])

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
        # Update test fields from form data
        test.value = request.form['value']
        test.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        # Add any other fields that can be edited
        try:
            db.session.commit()
            flash('Blood test updated successfully!', 'success')
            return redirect(url_for('index'))
        except:
            db.session.rollback()
            flash('Error updating blood test. Please try again.', 'danger')
            return redirect(url_for('edit_test', test_id=test.id))
    return render_template('edit.html', test=test)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
