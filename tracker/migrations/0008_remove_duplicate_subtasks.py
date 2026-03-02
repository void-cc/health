from django.db import migrations


# Sub-task numbers that were identified as duplicates and removed.
# For each duplicate (category, feature_type) pair, the lower-numbered
# sub-task was kept and the higher-numbered duplicate was removed.
DUPLICATE_SUBTASK_NUMBERS = [
    114,  # Micronutrients Api Syncing (duplicate of 109)
    134,  # Cognitive Tracking Automated Alerts (duplicate of 118)
    146,  # Circadian Rhythm Anomaly Detection (duplicate of 132)
    148,  # Circadian Rhythm Predictive Modeling (duplicate of 98)
    150,  # Macronutrients Automated Alerts (duplicate of 136)
    152,  # Garmin Reporting Tools (duplicate of 123)
    168,  # Telehealth Reporting Tools (duplicate of 113)
    171,  # Nutrition Reporting Tools (duplicate of 170)
    175,  # Genomics Secure Storage (duplicate of 108)
    176,  # Telehealth User Dashboard (duplicate of 106)
    179,  # DICOM Predictive Modeling (duplicate of 92)
    180,  # Machine Learning Data Pipeline (duplicate of 153)
]


def remove_duplicates(apps, schema_editor):
    IntegrationSubTask = apps.get_model('tracker', 'IntegrationSubTask')
    IntegrationSubTask.objects.filter(
        phase=11,
        sub_task_number__in=DUPLICATE_SUBTASK_NUMBERS,
    ).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0007_merge_20260302_0858'),
    ]

    operations = [
        migrations.RunPython(remove_duplicates, noop),
    ]
