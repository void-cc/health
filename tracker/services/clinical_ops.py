"""Clinical orchestration helpers for alerts and export payloads."""

from tracker.models import (
    BloodTest,
    VitalSign,
    MedicationSchedule,
    BodyComposition,
    SleepLog,
    CriticalAlert,
)


def run_critical_alert_check():
    """Run alert engine and return newly generated alerts."""
    return CriticalAlert.check_and_create_alerts()


def build_export_payload_for_user(user, include_global=False):
    """Build export payload for a user-scoped health snapshot."""
    blood_tests_qs = BloodTest.objects.filter(user=user).order_by('-date')
    vitals_qs = VitalSign.objects.filter(user=user).order_by('-date')
    medications_qs = MedicationSchedule.objects.filter(user=user).order_by('-start_date')
    sleep_qs = SleepLog.objects.filter(user=user).order_by('-date')
    if include_global:
        body_qs = BodyComposition.objects.all().order_by('-date')
    else:
        body_qs = BodyComposition.objects.none()

    return {
        'blood_tests': list(blood_tests_qs.values(
            'test_name', 'value', 'unit', 'date', 'normal_min', 'normal_max', 'category',
        )),
        'vitals': list(vitals_qs.values(
            'date', 'systolic_bp', 'diastolic_bp', 'heart_rate', 'bbt', 'respiratory_rate', 'spo2',
        )),
        'medications': list(medications_qs.values(
            'medication_name', 'dosage', 'frequency', 'start_date', 'end_date',
        )),
        'body_composition': list(body_qs.values(
            'date', 'body_fat_percentage', 'skeletal_muscle_mass', 'waist_circumference',
            'hip_circumference', 'waist_to_hip_ratio',
        )),
        'sleep_logs': list(sleep_qs.values(
            'date', 'total_sleep_minutes', 'deep_sleep_minutes', 'rem_minutes', 'sleep_quality_score',
        )),
    }
