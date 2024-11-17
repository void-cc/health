from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BloodTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    normal_min = db.Column(db.Float, nullable=False)
    normal_max = db.Column(db.Float, nullable=False)
