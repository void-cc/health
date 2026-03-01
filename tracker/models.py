from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class BloodTest(models.Model):
    test_name = models.CharField(max_length=100)
    value = models.FloatField()
    unit = models.CharField(max_length=20)
    date = models.DateField()
    normal_min = models.FloatField(null=True, blank=True)
    normal_max = models.FloatField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.test_name} on {self.date}"

class BloodTestInfo(models.Model):
    test_name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=20)
    normal_min = models.FloatField(null=True, blank=True)
    normal_max = models.FloatField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.test_name

class VitalSign(models.Model):
    date = models.DateField()
    weight = models.FloatField(null=True, blank=True)  # in kg or lbs
    heart_rate = models.IntegerField(null=True, blank=True) # bpm
    systolic_bp = models.IntegerField(null=True, blank=True) # mmHg
    diastolic_bp = models.IntegerField(null=True, blank=True) # mmHg
    # Phase 2 additions
    bbt = models.FloatField(null=True, blank=True)  # Basal Body Temperature in °C
    spo2 = models.FloatField(null=True, blank=True)  # Blood Oxygen Saturation in %
    respiratory_rate = models.IntegerField(null=True, blank=True)  # breaths per minute

    def __str__(self):
        return f"Vitals on {self.date}"


class BodyComposition(models.Model):
    date = models.DateField()
    body_fat_percentage = models.FloatField(null=True, blank=True)
    skeletal_muscle_mass = models.FloatField(null=True, blank=True)  # in kg
    bone_density = models.FloatField(null=True, blank=True)  # g/cm²
    waist_circumference = models.FloatField(null=True, blank=True)  # in cm
    hip_circumference = models.FloatField(null=True, blank=True)  # in cm
    waist_to_hip_ratio = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    def save(self, *args, **kwargs):
        if self.waist_circumference and self.hip_circumference and self.hip_circumference > 0:
            self.waist_to_hip_ratio = round(self.waist_circumference / self.hip_circumference, 3)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Body Composition on {self.date}"


class HydrationLog(models.Model):
    date = models.DateField()
    fluid_intake_ml = models.FloatField()  # in milliliters
    goal_ml = models.FloatField(null=True, blank=True, default=2500)  # daily goal in ml
    notes = models.TextField(blank=True, default='')

    @property
    def goal_percentage(self):
        if self.goal_ml and self.goal_ml > 0:
            return round((self.fluid_intake_ml / self.goal_ml) * 100, 1)
        return None

    def __str__(self):
        return f"Hydration on {self.date}: {self.fluid_intake_ml}ml"


class EnergyFatigueLog(models.Model):
    date = models.DateField()
    energy_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )  # 1=exhausted, 10=fully energized
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Energy on {self.date}: {self.energy_score}/10"


class CustomVitalDefinition(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=50)
    normal_min = models.FloatField(null=True, blank=True)
    normal_max = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.name} ({self.unit})"


class CustomVitalEntry(models.Model):
    definition = models.ForeignKey(CustomVitalDefinition, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    value = models.FloatField()
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.definition.name} on {self.date}: {self.value}"


BODY_REGIONS = [
    ('head', 'Head'),
    ('neck', 'Neck'),
    ('left_shoulder', 'Left Shoulder'),
    ('right_shoulder', 'Right Shoulder'),
    ('chest', 'Chest'),
    ('upper_back', 'Upper Back'),
    ('lower_back', 'Lower Back'),
    ('abdomen', 'Abdomen'),
    ('left_arm', 'Left Arm'),
    ('right_arm', 'Right Arm'),
    ('left_hand', 'Left Hand'),
    ('right_hand', 'Right Hand'),
    ('left_hip', 'Left Hip'),
    ('right_hip', 'Right Hip'),
    ('left_leg', 'Left Leg'),
    ('right_leg', 'Right Leg'),
    ('left_knee', 'Left Knee'),
    ('right_knee', 'Right Knee'),
    ('left_foot', 'Left Foot'),
    ('right_foot', 'Right Foot'),
]


class PainLog(models.Model):
    date = models.DateField()
    body_region = models.CharField(max_length=50, choices=BODY_REGIONS)
    pain_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )  # 1=minimal, 10=worst
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Pain on {self.date}: {self.get_body_region_display()} ({self.pain_level}/10)"


class RestingMetabolicRate(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    FORMULA_CHOICES = [
        ('mifflin', 'Mifflin-St Jeor'),
        ('harris', 'Harris-Benedict'),
    ]
    date = models.DateField()
    age = models.IntegerField()
    weight_kg = models.FloatField()
    height_cm = models.FloatField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    formula = models.CharField(max_length=20, choices=FORMULA_CHOICES, default='mifflin')
    rmr_value = models.FloatField(null=True, blank=True)  # kcal/day

    def calculate_rmr(self):
        if self.formula == 'mifflin':
            if self.gender == 'M':
                return round(10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5, 1)
            else:
                return round(10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age - 161, 1)
        else:  # harris-benedict
            if self.gender == 'M':
                return round(88.362 + 13.397 * self.weight_kg + 4.799 * self.height_cm - 5.677 * self.age, 1)
            else:
                return round(447.593 + 9.247 * self.weight_kg + 3.098 * self.height_cm - 4.330 * self.age, 1)

    def save(self, *args, **kwargs):
        self.rmr_value = self.calculate_rmr()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"RMR on {self.date}: {self.rmr_value} kcal/day"


class OrthostaticReading(models.Model):
    date = models.DateField()
    supine_hr = models.IntegerField(null=True, blank=True)  # lying down heart rate
    standing_hr = models.IntegerField(null=True, blank=True)  # standing heart rate
    supine_systolic = models.IntegerField(null=True, blank=True)
    supine_diastolic = models.IntegerField(null=True, blank=True)
    standing_systolic = models.IntegerField(null=True, blank=True)
    standing_diastolic = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    @property
    def hr_difference(self):
        if self.supine_hr is not None and self.standing_hr is not None:
            return self.standing_hr - self.supine_hr
        return None

    @property
    def systolic_drop(self):
        if self.supine_systolic is not None and self.standing_systolic is not None:
            return self.supine_systolic - self.standing_systolic
        return None

    def __str__(self):
        return f"Orthostatic on {self.date}"


class ReproductiveHealthLog(models.Model):
    PHASE_CHOICES = [
        ('menstrual', 'Menstrual'),
        ('follicular', 'Follicular'),
        ('ovulation', 'Ovulation'),
        ('luteal', 'Luteal'),
    ]
    date = models.DateField()
    cycle_day = models.IntegerField(null=True, blank=True)
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, blank=True, default='')
    flow_intensity = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )  # 0=none, 5=very heavy
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Reproductive Health on {self.date}"


class SymptomJournal(models.Model):
    SEVERITY_CHOICES = [
        (1, 'Mild'),
        (2, 'Moderate'),
        (3, 'Severe'),
        (4, 'Very Severe'),
        (5, 'Extreme'),
    ]
    date = models.DateField()
    symptom = models.CharField(max_length=200)
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=1)
    duration = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.symptom} on {self.date} (severity: {self.severity})"


class MetabolicLog(models.Model):
    date = models.DateField()
    blood_glucose = models.FloatField(null=True, blank=True)  # mg/dL
    insulin_level = models.FloatField(null=True, blank=True)  # µU/mL
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Metabolic on {self.date}"


class KetoneLog(models.Model):
    MEASUREMENT_CHOICES = [
        ('blood', 'Blood (mmol/L)'),
        ('urine', 'Urine (mg/dL)'),
        ('breath', 'Breath (ppm)'),
    ]
    date = models.DateField()
    value = models.FloatField()
    measurement_type = models.CharField(max_length=10, choices=MEASUREMENT_CHOICES, default='blood')
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Ketone on {self.date}: {self.value} ({self.get_measurement_type_display()})"
