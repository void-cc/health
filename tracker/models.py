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
