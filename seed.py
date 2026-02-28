from app import app, db
from models import BloodTest
from datetime import datetime

with app.app_context():
    # Insert a dummy test record
    test = BloodTest(
        test_name='Hemoglobin',
        value=15.0,
        unit='g/dL',
        date=datetime.now(),
        normal_min=13.8,
        normal_max=17.2
    )
    db.session.add(test)

    # Below normal range
    test2 = BloodTest(
        test_name='Hemoglobin',
        value=12.0,
        unit='g/dL',
        date=datetime.now(),
        normal_min=13.8,
        normal_max=17.2
    )
    db.session.add(test2)

    # Above normal range
    test3 = BloodTest(
        test_name='Hemoglobin',
        value=18.0,
        unit='g/dL',
        date=datetime.now(),
        normal_min=13.8,
        normal_max=17.2
    )
    db.session.add(test3)

    db.session.commit()
    print("Database seeded with test values.")
