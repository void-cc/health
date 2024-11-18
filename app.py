from flask import Flask, render_template, request, redirect, url_for
from models import db, BloodTest
from datetime import datetime

app = Flask(__name__)

# Configure Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blood_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Predefined Test Information
TEST_INFO = {
    'Hemoglobin': {'unit': 'g/dL', 'normal_min': 13.5, 'normal_max': 17.5},
    'Glucose': {'unit': 'mg/dL', 'normal_min': 70, 'normal_max': 99},
    'Cholesterol': {'unit': 'mg/dL', 'normal_min': 125, 'normal_max': 200},
    # Add more tests as needed
}

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
            return "Test not found.", 400

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
        return redirect(url_for('index'))

    return render_template('add.html', test_info=TEST_INFO)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
