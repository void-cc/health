from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone


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
        if (
            self.waist_circumference is not None
            and self.hip_circumference is not None
            and self.hip_circumference > 0
        ):
            self.waist_to_hip_ratio = round(self.waist_circumference / self.hip_circumference, 3)
        else:
            self.waist_to_hip_ratio = None
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
class DataPointAnnotation(models.Model):
    blood_test = models.ForeignKey(BloodTest, on_delete=models.CASCADE, null=True, blank=True, related_name='annotations')
    vital_sign = models.ForeignKey(VitalSign, on_delete=models.CASCADE, null=True, blank=True, related_name='annotations')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.blood_test:
            return f"Note on {self.blood_test}"
        return f"Note on {self.vital_sign}"


class DashboardWidget(models.Model):
    WIDGET_TYPES = [
        ('summary_cards', 'Summary Cards'),
        ('recent_results', 'Recent Blood Results'),
        ('vital_signs', 'Latest Vital Signs'),
        ('blood_charts', 'Blood Test Charts'),
        ('vitals_charts', 'Vital Signs Charts'),
        ('comparative_bars', 'Comparative Bar Charts'),
        ('boxplots', 'Box Plots'),
    ]
    widget_type = models.CharField(max_length=50, choices=WIDGET_TYPES, unique=True)
    position = models.IntegerField(default=0)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.get_widget_type_display()} (pos {self.position})"


class UserProfile(models.Model):
    BIOLOGICAL_SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System'),
    ]
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('user', 'Standard User'),
        ('practitioner', 'Medical Practitioner'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(null=True, blank=True)
    biological_sex = models.CharField(max_length=20, choices=BIOLOGICAL_SEX_CHOICES, blank=True, default='')
    height_cm = models.FloatField(null=True, blank=True)
    genetic_baseline_info = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    theme_preference = models.CharField(max_length=20, choices=THEME_CHOICES, default='system')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class SecurityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('login_failed', 'Login Failed'),
        ('password_changed', 'Password Changed'),
        ('password_reset', 'Password Reset'),
        ('mfa_enabled', 'MFA Enabled'),
        ('mfa_disabled', 'MFA Disabled'),
        ('profile_updated', 'Profile Updated'),
        ('account_deleted', 'Account Deleted'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='security_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    device_type = models.CharField(max_length=50, blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='active_sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    device_type = models.CharField(max_length=50, blank=True, default='')
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']

    def __str__(self):
        return f"Session for {self.user.username} from {self.ip_address}"


class PrivacyPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='privacy_preferences')
    allow_data_sharing = models.BooleanField(default=False)
    allow_analytics = models.BooleanField(default=False)
    allow_research_use = models.BooleanField(default=False)
    data_retention_days = models.IntegerField(default=365, validators=[MinValueValidator(30)])
    show_profile_publicly = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Privacy preferences for {self.user.username}"
# ===== Phase 5: Wearable Integrations =====

WEARABLE_PLATFORMS = [
    ('apple_health', 'Apple Health'),
    ('fitbit', 'Fitbit'),
    ('garmin', 'Garmin Connect'),
    ('oura', 'Oura Ring'),
    ('google_fit', 'Google Fit'),
    ('withings', 'Withings'),
    ('samsung_health', 'Samsung Health'),
    ('dexcom_cgm', 'Dexcom CGM'),
    ('strava', 'Strava'),
]


class WearableDevice(models.Model):
    platform = models.CharField(max_length=50, choices=WEARABLE_PLATFORMS)
    device_name = models.CharField(max_length=200, blank=True, default='')
    access_token = models.TextField(blank=True, default='')
    refresh_token = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_platform_display()} - {self.device_name or 'Unknown'}"


class WearableSyncLog(models.Model):
    SYNC_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='sync_logs')
    status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default='pending')
    records_synced = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Sync {self.device.get_platform_display()} - {self.status} ({self.started_at})"


# ===== Phase 6: Sleep and Nutrition Tracking =====

class SleepLog(models.Model):
    date = models.DateField()
    bedtime = models.TimeField(null=True, blank=True)
    wake_time = models.TimeField(null=True, blank=True)
    total_sleep_minutes = models.IntegerField(null=True, blank=True)
    rem_minutes = models.IntegerField(null=True, blank=True)
    deep_sleep_minutes = models.IntegerField(null=True, blank=True)
    light_sleep_minutes = models.IntegerField(null=True, blank=True)
    awake_minutes = models.IntegerField(null=True, blank=True)
    sleep_quality_score = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    @property
    def sleep_efficiency(self):
        if self.total_sleep_minutes is not None and self.awake_minutes is not None:
            total = self.total_sleep_minutes + self.awake_minutes
            if total > 0:
                return round((self.total_sleep_minutes / total) * 100, 1)
        return None

    def calculate_quality_score(self):
        """Algorithmic calculation of sleep quality based on sleep architecture.

        Scoring factors (0-100 scale):
        - Sleep efficiency (40% weight): percentage of time in bed spent asleep
        - Deep sleep ratio (25% weight): deep sleep as % of total (ideal ~20%)
        - REM ratio (25% weight): REM as % of total (ideal ~25%)
        - Low awakenings (10% weight): fewer awake minutes = better score
        """
        if self.total_sleep_minutes is None or self.total_sleep_minutes == 0:
            return None

        score = 0.0

        # Efficiency component (40 points max)
        efficiency = self.sleep_efficiency
        if efficiency is not None:
            score += min(efficiency / 100.0, 1.0) * 40.0

        # Deep sleep component (25 points max) — ideal ~20% of total
        if self.deep_sleep_minutes is not None:
            deep_ratio = self.deep_sleep_minutes / self.total_sleep_minutes
            deep_score = min(deep_ratio / 0.20, 1.0)
            score += deep_score * 25.0

        # REM component (25 points max) — ideal ~25% of total
        if self.rem_minutes is not None:
            rem_ratio = self.rem_minutes / self.total_sleep_minutes
            rem_score = min(rem_ratio / 0.25, 1.0)
            score += rem_score * 25.0

        # Low awakenings component (10 points max)
        if self.awake_minutes is not None:
            awake_penalty = max(0.0, 1.0 - (self.awake_minutes / 60.0))
            score += awake_penalty * 10.0

        return round(score, 1)

    @property
    def sleep_trend(self):
        """Return recent sleep efficiency trend: 'improving', 'declining', or 'stable'.

        Compares average efficiency of last 7 entries vs previous 7 entries.
        """
        recent_logs = SleepLog.objects.filter(
            date__lt=self.date
        ).order_by('-date')[:14]
        recent_list = list(recent_logs)
        if len(recent_list) < 4:
            return None
        mid = min(7, len(recent_list) // 2)
        recent_half = recent_list[:mid]
        older_half = recent_list[mid:mid * 2]
        if not older_half:
            return None

        def avg_efficiency(logs):
            vals = [l.sleep_efficiency for l in logs if l.sleep_efficiency is not None]
            return sum(vals) / len(vals) if vals else None

        recent_avg = avg_efficiency(recent_half)
        older_avg = avg_efficiency(older_half)
        if recent_avg is None or older_avg is None:
            return None
        diff = recent_avg - older_avg
        if diff > 2.0:
            return 'improving'
        elif diff < -2.0:
            return 'declining'
        return 'stable'

    def __str__(self):
        return f"Sleep on {self.date}"


class CircadianRhythmLog(models.Model):
    date = models.DateField()
    wake_time = models.TimeField(null=True, blank=True)
    sleep_onset = models.TimeField(null=True, blank=True)
    peak_energy_time = models.TimeField(null=True, blank=True)
    lowest_energy_time = models.TimeField(null=True, blank=True)
    light_exposure_minutes = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    @property
    def optimal_sleep_window(self):
        """Suggest an optimal sleep window based on recorded circadian patterns.

        Uses average sleep onset and wake time from recent entries to suggest
        the best sleep/wake times for this individual.
        """
        from datetime import timedelta, datetime as dt
        recent = CircadianRhythmLog.objects.filter(
            sleep_onset__isnull=False, wake_time__isnull=False,
        ).order_by('-date')[:7]
        recent_list = list(recent)
        if not recent_list:
            return None

        def time_to_minutes(t):
            mins = t.hour * 60 + t.minute
            # Treat times before 6 AM as next-day (add 24h)
            if mins < 360:
                mins += 1440
            return mins

        onset_mins = [time_to_minutes(r.sleep_onset) for r in recent_list]
        wake_mins = [time_to_minutes(r.wake_time) for r in recent_list]
        avg_onset = sum(onset_mins) // len(onset_mins)
        avg_wake = sum(wake_mins) // len(wake_mins)
        # Convert back to HH:MM
        onset_h, onset_m = divmod(avg_onset % 1440, 60)
        wake_h, wake_m = divmod(avg_wake % 1440, 60)
        return {
            'suggested_bedtime': f"{onset_h:02d}:{onset_m:02d}",
            'suggested_wake_time': f"{wake_h:02d}:{wake_m:02d}",
        }

    def __str__(self):
        return f"Circadian Rhythm on {self.date}"


class DreamJournal(models.Model):
    date = models.DateField()
    dream_description = models.TextField(blank=True, default='')
    lucidity_level = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    mood_on_waking = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Dream Journal on {self.date}"


class MacronutrientLog(models.Model):
    date = models.DateField()
    protein_grams = models.FloatField(null=True, blank=True)
    carbohydrate_grams = models.FloatField(null=True, blank=True)
    fat_grams = models.FloatField(null=True, blank=True)
    calories = models.FloatField(null=True, blank=True)
    fiber_grams = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    @property
    def total_macros_grams(self):
        p = self.protein_grams or 0
        c = self.carbohydrate_grams or 0
        f = self.fat_grams or 0
        return round(p + c + f, 1)

    def __str__(self):
        return f"Macros on {self.date}"


class MicronutrientLog(models.Model):
    date = models.DateField()
    nutrient_name = models.CharField(max_length=100)
    amount = models.FloatField()
    unit = models.CharField(max_length=20, default='mg')
    deficiency_risk = models.CharField(max_length=20, blank=True, default='',
        help_text='Risk level mapped from blood test results: low, moderate, high')
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.nutrient_name} on {self.date}: {self.amount}{self.unit}"


class FoodEntry(models.Model):
    date = models.DateField()
    food_name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=100, blank=True, default='')
    serving_size = models.CharField(max_length=100, blank=True, default='')
    calories = models.FloatField(null=True, blank=True)
    protein_grams = models.FloatField(null=True, blank=True)
    carbohydrate_grams = models.FloatField(null=True, blank=True)
    fat_grams = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True, default='',
        help_text='Data source: manual, barcode_scan, usda, openfoodfacts')
    food_database_id = models.CharField(max_length=100, blank=True, default='',
        help_text='External food database identifier (e.g., USDA FDC ID or OpenFoodFacts ID)')
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.food_name} on {self.date}"


class FastingLog(models.Model):
    date = models.DateField()
    fast_start = models.DateTimeField(null=True, blank=True)
    fast_end = models.DateTimeField(null=True, blank=True)
    target_hours = models.FloatField(null=True, blank=True)
    actual_hours = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    @property
    def goal_met(self):
        if self.actual_hours is not None and self.target_hours is not None and self.target_hours > 0:
            return self.actual_hours >= self.target_hours
        return None

    def __str__(self):
        return f"Fasting on {self.date}"


class CaffeineAlcoholLog(models.Model):
    SUBSTANCE_CHOICES = [
        ('caffeine', 'Caffeine'),
        ('alcohol', 'Alcohol'),
    ]
    date = models.DateField()
    substance = models.CharField(max_length=20, choices=SUBSTANCE_CHOICES)
    amount_mg = models.FloatField(null=True, blank=True)
    drink_name = models.CharField(max_length=200, blank=True, default='')
    time_consumed = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.get_substance_display()} on {self.date}"


# ===== Phase 7: Multi-User Release Preparations =====

class FamilyAccount(models.Model):
    primary_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='family_members')
    member_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=100, blank=True, default='')
    is_minor = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member_name} (under {self.primary_user.user.username})"


class EncryptionKey(models.Model):
    key_identifier = models.CharField(max_length=255, unique=True)
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Key {self.key_identifier}"


class AuditLog(models.Model):
    action = models.CharField(max_length=200)
    details = models.TextField(blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} at {self.created_at}"


class APIRateLimitConfig(models.Model):
    endpoint = models.CharField(max_length=255, unique=True)
    max_requests_per_minute = models.IntegerField(default=60)
    max_requests_per_hour = models.IntegerField(default=1000)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Rate Limit: {self.endpoint} ({self.max_requests_per_minute}/min)"


class ConsentLog(models.Model):
    consent_type = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"Consent: {self.consent_type} v{self.version}"


class TenantConfig(models.Model):
    tenant_name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    data_isolation_level = models.CharField(max_length=50, default='full')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tenant: {self.tenant_name}"


class AdminTelemetry(models.Model):
    metric_name = models.CharField(max_length=200)
    metric_value = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.metric_name}: {self.metric_value}"


# ===== Phase 8: Advanced Health Analytics and AI =====

class PredictiveBiomarker(models.Model):
    biomarker_name = models.CharField(max_length=100)
    predicted_value = models.FloatField()
    confidence_percent = models.FloatField(null=True, blank=True)
    prediction_date = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Prediction: {self.biomarker_name} on {self.prediction_date}"


class HealthReport(models.Model):
    REPORT_TYPES = [
        ('monthly', 'Monthly Summary'),
        ('quarterly', 'Quarterly Review'),
        ('annual', 'Annual Report'),
    ]
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='monthly')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, default='')
    period_start = models.DateField()
    period_end = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.period_start} - {self.period_end})"


class ClinicalTrialMatch(models.Model):
    trial_id = models.CharField(max_length=100)
    trial_title = models.CharField(max_length=500)
    condition = models.CharField(max_length=200)
    match_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True, default='')
    url = models.URLField(blank=True, default='')
    found_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trial: {self.trial_title[:50]}"


class BiologicalAgeCalculation(models.Model):
    date = models.DateField()
    chronological_age = models.FloatField()
    biological_age = models.FloatField()
    method = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    @property
    def age_difference(self):
        return round(self.biological_age - self.chronological_age, 1)

    def __str__(self):
        return f"Bio Age on {self.date}: {self.biological_age} (chrono: {self.chronological_age})"


class MedicationSchedule(models.Model):
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    time_of_day = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.medication_name} - {self.dosage}"


class PharmacologicalInteraction(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    medication_a = models.CharField(max_length=200)
    medication_b = models.CharField(max_length=200)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low')
    description = models.TextField(blank=True, default='')
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interaction: {self.medication_a} x {self.medication_b} ({self.severity})"


class HealthGoal(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    target_value = models.FloatField(null=True, blank=True)
    current_value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField()
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def progress_percent(self):
        if self.target_value is not None and self.current_value is not None and self.target_value > 0:
            return round((self.current_value / self.target_value) * 100, 1)
        return None

    def __str__(self):
        return f"Goal: {self.title} ({self.status})"


class CriticalAlert(models.Model):
    ALERT_LEVELS = [
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('emergency', 'Emergency'),
    ]
    metric_name = models.CharField(max_length=100)
    metric_value = models.FloatField()
    threshold_value = models.FloatField()
    alert_level = models.CharField(max_length=20, choices=ALERT_LEVELS, default='warning')
    message = models.TextField(blank=True, default='')
    acknowledged = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert: {self.metric_name} ({self.alert_level})"


# ===== Phase 9: Export, Sharing, and Practitioner Access =====

class SecureViewingLink(models.Model):
    token = models.CharField(max_length=255, unique=True)
    data_types = models.CharField(max_length=500, blank=True, default='')
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    access_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Secure Link (expires {self.expires_at})"


class PractitionerAccess(models.Model):
    ACCESS_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('revoked', 'Revoked'),
    ]
    practitioner_name = models.CharField(max_length=200)
    practitioner_email = models.EmailField()
    specialty = models.CharField(max_length=100, blank=True, default='')
    access_status = models.CharField(max_length=20, choices=ACCESS_STATUS, default='pending')
    granted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Dr. {self.practitioner_name} - {self.access_status}"


class IntakeSummary(models.Model):
    title = models.CharField(max_length=200)
    summary_text = models.TextField(blank=True, default='')
    conditions = models.TextField(blank=True, default='')
    medications = models.TextField(blank=True, default='')
    allergies = models.TextField(blank=True, default='')
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Intake Summary: {self.title}"


class DataExportRequest(models.Model):
    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('csv', 'CSV'),
        ('pdf', 'PDF'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    export_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='json')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    file_path = models.CharField(max_length=500, blank=True, default='')

    def __str__(self):
        return f"Export ({self.export_format}) - {self.status}"


class StakeholderEmail(models.Model):
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    recipient_name = models.CharField(max_length=200)
    recipient_email = models.EmailField()
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    is_active = models.BooleanField(default=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.recipient_name} ({self.frequency})"


# ===== Phases 10-12: Integration Sub-tasks =====

INTEGRATION_CATEGORIES = [
    ('genomics', 'Genomics'),
    ('blockchain', 'Blockchain'),
    ('reproductive_health', 'Reproductive Health'),
    ('dicom', 'DICOM'),
    ('mental_health', 'Mental Health'),
    ('predictive_analytics', 'Predictive Analytics'),
    ('ihe_xdm', 'IHE_XDM'),
    ('machine_learning', 'Machine Learning'),
    ('macronutrients', 'Macronutrients'),
    ('micronutrients', 'Micronutrients'),
    ('nutrition', 'Nutrition'),
    ('cognitive_tracking', 'Cognitive Tracking'),
    ('telehealth', 'Telehealth'),
    ('garmin', 'Garmin'),
    ('fitbit', 'Fitbit'),
    ('oura', 'Oura'),
    ('apple_health', 'Apple Health'),
    ('withings', 'Withings'),
    ('sleep_architecture', 'Sleep Architecture'),
    ('circadian_rhythm', 'Circadian Rhythm'),
    ('chronic_disease', 'Chronic Disease'),
    ('gamification', 'Gamification'),
    ('hl7_v3', 'HL7 v3'),
    ('fhir_r4', 'FHIR R4'),
    ('decentralized_identity', 'Decentralized Identity'),
]

INTEGRATION_FEATURE_TYPES = [
    ('export', 'Export Capabilities'),
    ('data_pipeline', 'Data Pipeline'),
    ('predictive_modeling', 'Predictive Modeling'),
    ('reporting', 'Reporting Tools'),
    ('anomaly_detection', 'Anomaly Detection'),
    ('user_dashboard', 'User Dashboard'),
    ('api_syncing', 'API Syncing'),
    ('mobile_integration', 'Mobile Integration'),
    ('secure_storage', 'Secure Storage'),
    ('data_visualization', 'Data Visualization'),
    ('real_time_monitoring', 'Real-Time Monitoring'),
    ('automated_alerts', 'Automated Alerts'),
]


class IntegrationConfig(models.Model):
    category = models.CharField(max_length=50, choices=INTEGRATION_CATEGORIES)
    feature_type = models.CharField(max_length=50, choices=INTEGRATION_FEATURE_TYPES)
    is_enabled = models.BooleanField(default=False)
    configuration = models.JSONField(default=dict, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['category', 'feature_type']

    def __str__(self):
        return f"{self.get_category_display()} - {self.get_feature_type_display()}"


class IntegrationSubTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    PHASE_CHOICES = [
        (10, 'Phase 10: Genomics & Personalized Medicine'),
        (11, 'Phase 11: Interoperability'),
        (12, 'Phase 12: Continuous Monitoring & Alerts'),
    ]
    phase = models.IntegerField(choices=PHASE_CHOICES)
    sub_task_number = models.IntegerField()
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=50, choices=INTEGRATION_CATEGORIES)
    feature_type = models.CharField(max_length=50, choices=INTEGRATION_FEATURE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    details = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['phase', 'sub_task_number']
        ordering = ['phase', 'sub_task_number']

    def __str__(self):
        return f"Phase {self.phase} Sub-task {self.sub_task_number}: {self.title}"
