from django.db import models

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

    def __str__(self):
        return f"Vitals on {self.date}"


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
