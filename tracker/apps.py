from django.apps import AppConfig


import os
import csv
class TrackerConfig(AppConfig):
    name = "tracker"

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(self._load_initial_data, sender=self)

    @staticmethod
    def _load_initial_data(sender, **kwargs):
        from .models import BloodTestInfo
        try:
            if BloodTestInfo.objects.exists() is False:
                csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'blood_tests.csv')
                if os.path.exists(csv_path):
                    with open(csv_path, mode='r', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            test_name = row['test_name']
                            unit = row['unit']
                            normal_min = row['normal_min']
                            normal_max = row['normal_max']
                            category = row.get('category', 'Uncategorized')

                            try:
                                normal_min = float(normal_min) if normal_min else None
                                normal_max = float(normal_max) if normal_max else None
                            except ValueError:
                                normal_min = None
                                normal_max = None

                            BloodTestInfo.objects.create(
                                test_name=test_name,
                                unit=unit,
                                normal_min=normal_min,
                                normal_max=normal_max,
                                category=category
                            )
        except Exception as e:
            pass
