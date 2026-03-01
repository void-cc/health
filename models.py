from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BloodTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    normal_min = db.Column(db.Float, nullable=True)
    normal_max = db.Column(db.Float, nullable=True)
    category = db.Column(db.String(100), nullable=True)


class BloodTestInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), unique=True, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    normal_min = db.Column(db.Float, nullable=True)
    normal_max = db.Column(db.Float, nullable=True)
    category = db.Column(db.String(100), nullable=True)

class VitalSign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Float, nullable=True)  # in kg or lbs
    heart_rate = db.Column(db.Integer, nullable=True) # bpm
    systolic_bp = db.Column(db.Integer, nullable=True) # mmHg
    diastolic_bp = db.Column(db.Integer, nullable=True) # mmHg
