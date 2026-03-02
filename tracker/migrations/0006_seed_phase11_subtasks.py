from django.db import migrations


PHASE_11_SUBTASKS = [
    (91, "Macronutrients User Dashboard", "macronutrients", "user_dashboard"),
    (92, "DICOM Predictive Modeling", "dicom", "predictive_modeling"),
    (93, "Blockchain Data Visualization", "blockchain", "data_visualization"),
    (94, "Decentralized Identity User Dashboard", "decentralized_identity", "user_dashboard"),
    (95, "Predictive Analytics Predictive Modeling", "predictive_analytics", "predictive_modeling"),
    (96, "Nutrition Automated Alerts", "nutrition", "automated_alerts"),
    (97, "Decentralized Identity Predictive Modeling", "decentralized_identity", "predictive_modeling"),
    (98, "Circadian Rhythm Predictive Modeling", "circadian_rhythm", "predictive_modeling"),
    (99, "IHE_XDM Predictive Modeling", "ihe_xdm", "predictive_modeling"),
    (100, "Genomics Data Visualization", "genomics", "data_visualization"),
    (101, "Withings Anomaly Detection", "withings", "anomaly_detection"),
    (102, "Fitbit Data Visualization", "fitbit", "data_visualization"),
    (103, "Micronutrients Secure Storage", "micronutrients", "secure_storage"),
    (104, "IHE_XDM Data Pipeline", "ihe_xdm", "data_pipeline"),
    (105, "Decentralized Identity Data Visualization", "decentralized_identity", "data_visualization"),
    (106, "Telehealth User Dashboard", "telehealth", "user_dashboard"),
    (107, "Fitbit Reporting Tools", "fitbit", "reporting"),
    (108, "Genomics Secure Storage", "genomics", "secure_storage"),
    (109, "Micronutrients Api Syncing", "micronutrients", "api_syncing"),
    (110, "Circadian Rhythm Api Syncing", "circadian_rhythm", "api_syncing"),
    (111, "Garmin Data Visualization", "garmin", "data_visualization"),
    (112, "Nutrition Real-Time Monitoring", "nutrition", "real_time_monitoring"),
    (113, "Telehealth Reporting Tools", "telehealth", "reporting"),
    (114, "Micronutrients Api Syncing", "micronutrients", "api_syncing"),
    (115, "Decentralized Identity Data Pipeline", "decentralized_identity", "data_pipeline"),
    (116, "Circadian Rhythm Real-Time Monitoring", "circadian_rhythm", "real_time_monitoring"),
    (117, "Chronic Disease User Dashboard", "chronic_disease", "user_dashboard"),
    (118, "Cognitive Tracking Automated Alerts", "cognitive_tracking", "automated_alerts"),
    (119, "DICOM Anomaly Detection", "dicom", "anomaly_detection"),
    (120, "DICOM Data Pipeline", "dicom", "data_pipeline"),
    (121, "Predictive Analytics Data Pipeline", "predictive_analytics", "data_pipeline"),
    (122, "IHE_XDM Export Capabilities", "ihe_xdm", "export"),
    (123, "Garmin Reporting Tools", "garmin", "reporting"),
    (124, "FHIR R4 Predictive Modeling", "fhir_r4", "predictive_modeling"),
    (125, "Blockchain Anomaly Detection", "blockchain", "anomaly_detection"),
    (126, "FHIR R4 Export Capabilities", "fhir_r4", "export"),
    (127, "IHE_XDM Reporting Tools", "ihe_xdm", "reporting"),
    (128, "Blockchain Reporting Tools", "blockchain", "reporting"),
    (129, "Predictive Analytics Real-Time Monitoring", "predictive_analytics", "real_time_monitoring"),
    (130, "Cognitive Tracking Api Syncing", "cognitive_tracking", "api_syncing"),
    (131, "Nutrition Api Syncing", "nutrition", "api_syncing"),
    (132, "Circadian Rhythm Anomaly Detection", "circadian_rhythm", "anomaly_detection"),
    (133, "Gamification User Dashboard", "gamification", "user_dashboard"),
    (134, "Cognitive Tracking Automated Alerts", "cognitive_tracking", "automated_alerts"),
    (135, "Nutrition Predictive Modeling", "nutrition", "predictive_modeling"),
    (136, "Macronutrients Automated Alerts", "macronutrients", "automated_alerts"),
    (137, "Nutrition Secure Storage", "nutrition", "secure_storage"),
    (138, "Garmin Anomaly Detection", "garmin", "anomaly_detection"),
    (139, "Predictive Analytics Secure Storage", "predictive_analytics", "secure_storage"),
    (140, "Reproductive Health Api Syncing", "reproductive_health", "api_syncing"),
    (141, "Fitbit Anomaly Detection", "fitbit", "anomaly_detection"),
    (142, "Gamification Export Capabilities", "gamification", "export"),
    (143, "Telehealth Export Capabilities", "telehealth", "export"),
    (144, "HL7 v3 Reporting Tools", "hl7_v3", "reporting"),
    (145, "Fitbit Predictive Modeling", "fitbit", "predictive_modeling"),
    (146, "Circadian Rhythm Anomaly Detection", "circadian_rhythm", "anomaly_detection"),
    (147, "Gamification Data Pipeline", "gamification", "data_pipeline"),
    (148, "Circadian Rhythm Predictive Modeling", "circadian_rhythm", "predictive_modeling"),
    (149, "Circadian Rhythm User Dashboard", "circadian_rhythm", "user_dashboard"),
    (150, "Macronutrients Automated Alerts", "macronutrients", "automated_alerts"),
    (151, "Predictive Analytics Reporting Tools", "predictive_analytics", "reporting"),
    (152, "Garmin Reporting Tools", "garmin", "reporting"),
    (153, "Machine Learning Data Pipeline", "machine_learning", "data_pipeline"),
    (154, "Garmin Real-Time Monitoring", "garmin", "real_time_monitoring"),
    (155, "Mental Health Real-Time Monitoring", "mental_health", "real_time_monitoring"),
    (156, "IHE_XDM Api Syncing", "ihe_xdm", "api_syncing"),
    (157, "Withings Api Syncing", "withings", "api_syncing"),
    (158, "Oura User Dashboard", "oura", "user_dashboard"),
    (159, "Sleep Architecture Secure Storage", "sleep_architecture", "secure_storage"),
    (160, "Micronutrients Predictive Modeling", "micronutrients", "predictive_modeling"),
    (161, "Decentralized Identity Real-Time Monitoring", "decentralized_identity", "real_time_monitoring"),
    (162, "Circadian Rhythm Reporting Tools", "circadian_rhythm", "reporting"),
    (163, "Predictive Analytics User Dashboard", "predictive_analytics", "user_dashboard"),
    (164, "Blockchain Export Capabilities", "blockchain", "export"),
    (165, "Decentralized Identity Api Syncing", "decentralized_identity", "api_syncing"),
    (166, "Macronutrients Secure Storage", "macronutrients", "secure_storage"),
    (167, "Genomics Anomaly Detection", "genomics", "anomaly_detection"),
    (168, "Telehealth Reporting Tools", "telehealth", "reporting"),
    (169, "Blockchain Real-Time Monitoring", "blockchain", "real_time_monitoring"),
    (170, "Nutrition Reporting Tools", "nutrition", "reporting"),
    (171, "Nutrition Reporting Tools", "nutrition", "reporting"),
    (172, "Nutrition Mobile Integration", "nutrition", "mobile_integration"),
    (173, "Genomics Api Syncing", "genomics", "api_syncing"),
    (174, "FHIR R4 Anomaly Detection", "fhir_r4", "anomaly_detection"),
    (175, "Genomics Secure Storage", "genomics", "secure_storage"),
    (176, "Telehealth User Dashboard", "telehealth", "user_dashboard"),
    (177, "IHE_XDM Secure Storage", "ihe_xdm", "secure_storage"),
    (178, "Chronic Disease Export Capabilities", "chronic_disease", "export"),
    (179, "DICOM Predictive Modeling", "dicom", "predictive_modeling"),
    (180, "Machine Learning Data Pipeline", "machine_learning", "data_pipeline"),
]


def seed_phase11(apps, schema_editor):
    IntegrationSubTask = apps.get_model('tracker', 'IntegrationSubTask')
    for sub_task_number, title, category, feature_type in PHASE_11_SUBTASKS:
        IntegrationSubTask.objects.get_or_create(
            phase=11,
            sub_task_number=sub_task_number,
            defaults={
                'title': title,
                'category': category,
                'feature_type': feature_type,
                'status': 'pending',
                'details': '',
            },
        )


def reverse_phase11(apps, schema_editor):
    IntegrationSubTask = apps.get_model('tracker', 'IntegrationSubTask')
    IntegrationSubTask.objects.filter(phase=11, sub_task_number__gte=91, sub_task_number__lte=180).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_merge_20260302_0715'),
    ]

    operations = [
        migrations.RunPython(seed_phase11, reverse_phase11),
    ]
