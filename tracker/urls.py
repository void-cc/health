from django.urls import path
from . import views
from . import auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('history/', views.history, name='history'),
    path('vitals/', views.vitals, name='vitals'),
    path('add/', views.add_test, name='add_test'),
    path('add_test_info/', views.add_test_info, name='add_test_info'),
    path('delete/<int:test_id>/', views.delete_test, name='delete_test'),
    path('edit/<int:test_id>/', views.edit_test, name='edit_test'),
    path('vitals/add/', views.add_vitals, name='add_vitals'),
    path('vitals/edit/<int:vital_id>/', views.edit_vitals, name='edit_vitals'),
    path('vitals/delete/<int:vital_id>/', views.delete_vitals, name='delete_vitals'),
    path('chart/<str:test_name>/', views.chart, name='chart'),
    path('blood_tests/charts/', views.blood_tests_charts, name='blood_tests_charts'),
    path('blood_tests/boxplots/', views.blood_tests_boxplots, name='blood_tests_boxplots'),
    path('blood_tests/bar_charts/', views.comparative_bar_charts, name='comparative_bar_charts'),
    path('vitals/charts/', views.vitals_charts, name='vitals_charts'),
    path('scatter/', views.scatter_plots, name='scatter_plots'),
    path('import/', views.import_data, name='import_data'),
    path('export/', views.export_data, name='export_data'),

    # Body Composition
    path('body-composition/', views.body_composition_list, name='body_composition_list'),
    path('body-composition/add/', views.body_composition_add, name='body_composition_add'),
    path('body-composition/edit/<int:pk>/', views.body_composition_edit, name='body_composition_edit'),
    path('body-composition/delete/<int:pk>/', views.body_composition_delete, name='body_composition_delete'),

    # Hydration
    path('hydration/', views.hydration_list, name='hydration_list'),
    path('hydration/add/', views.hydration_add, name='hydration_add'),
    path('hydration/edit/<int:pk>/', views.hydration_edit, name='hydration_edit'),
    path('hydration/delete/<int:pk>/', views.hydration_delete, name='hydration_delete'),

    # Energy & Fatigue
    path('energy/', views.energy_list, name='energy_list'),
    path('energy/add/', views.energy_add, name='energy_add'),
    path('energy/edit/<int:pk>/', views.energy_edit, name='energy_edit'),
    path('energy/delete/<int:pk>/', views.energy_delete, name='energy_delete'),

    # Custom Vitals
    path('custom-vitals/', views.custom_vitals_list, name='custom_vitals_list'),
    path('custom-vitals/define/', views.custom_vital_define, name='custom_vital_define'),
    path('custom-vitals/add/', views.custom_vital_add_entry, name='custom_vital_add_entry'),
    path('custom-vitals/edit/<int:pk>/', views.custom_vital_edit_entry, name='custom_vital_edit_entry'),
    path('custom-vitals/delete/<int:pk>/', views.custom_vital_delete_entry, name='custom_vital_delete_entry'),

    # Pain Mapping
    path('pain/', views.pain_list, name='pain_list'),
    path('pain/add/', views.pain_add, name='pain_add'),
    path('pain/edit/<int:pk>/', views.pain_edit, name='pain_edit'),
    path('pain/delete/<int:pk>/', views.pain_delete, name='pain_delete'),

    # Resting Metabolic Rate
    path('rmr/', views.rmr_list, name='rmr_list'),
    path('rmr/add/', views.rmr_add, name='rmr_add'),
    path('rmr/edit/<int:pk>/', views.rmr_edit, name='rmr_edit'),
    path('rmr/delete/<int:pk>/', views.rmr_delete, name='rmr_delete'),

    # Orthostatic Tracking
    path('orthostatic/', views.orthostatic_list, name='orthostatic_list'),
    path('orthostatic/add/', views.orthostatic_add, name='orthostatic_add'),
    path('orthostatic/edit/<int:pk>/', views.orthostatic_edit, name='orthostatic_edit'),
    path('orthostatic/delete/<int:pk>/', views.orthostatic_delete, name='orthostatic_delete'),

    # Reproductive Health
    path('reproductive/', views.reproductive_list, name='reproductive_list'),
    path('reproductive/add/', views.reproductive_add, name='reproductive_add'),
    path('reproductive/edit/<int:pk>/', views.reproductive_edit, name='reproductive_edit'),
    path('reproductive/delete/<int:pk>/', views.reproductive_delete, name='reproductive_delete'),

    # Symptom Journaling
    path('symptoms/', views.symptom_list, name='symptom_list'),
    path('symptoms/add/', views.symptom_add, name='symptom_add'),
    path('symptoms/edit/<int:pk>/', views.symptom_edit, name='symptom_edit'),
    path('symptoms/delete/<int:pk>/', views.symptom_delete, name='symptom_delete'),

    # Metabolic Monitoring
    path('metabolic/', views.metabolic_list, name='metabolic_list'),
    path('metabolic/add/', views.metabolic_add, name='metabolic_add'),
    path('metabolic/edit/<int:pk>/', views.metabolic_edit, name='metabolic_edit'),
    path('metabolic/delete/<int:pk>/', views.metabolic_delete, name='metabolic_delete'),

    # Ketone Tracking
    path('ketones/', views.ketone_list, name='ketone_list'),
    path('ketones/add/', views.ketone_add, name='ketone_add'),
    path('ketones/edit/<int:pk>/', views.ketone_edit, name='ketone_edit'),
    path('ketones/delete/<int:pk>/', views.ketone_delete, name='ketone_delete'),
    # Data Point Annotations
    path('annotations/add/<str:model_type>/<int:object_id>/', views.add_annotation, name='add_annotation'),
    path('annotations/delete/<int:annotation_id>/', views.delete_annotation, name='delete_annotation'),
    # Bulk Data Editing
    path('bulk_edit/', views.bulk_edit, name='bulk_edit'),
    # Customizable Dashboard
    path('dashboard/customize/', views.customize_dashboard, name='customize_dashboard'),
    path('dashboard/update_widgets/', views.update_widgets, name='update_widgets'),

    # Global Search API
    path('api/search/', views.global_search, name='global_search'),

    # User Authentication and Profiles
    path('accounts/register/', auth_views.register_view, name='register'),
    path('accounts/login/', auth_views.login_view, name='login'),
    path('accounts/logout/', auth_views.logout_view, name='logout'),
    path('accounts/profile/', auth_views.profile_view, name='profile'),
    path('accounts/change-password/', auth_views.change_password_view, name='change_password'),
    path('accounts/security-log/', auth_views.security_log_view, name='security_log'),
    path('accounts/sessions/', auth_views.active_sessions_view, name='active_sessions'),
    path('accounts/sessions/terminate/<int:session_id>/', auth_views.terminate_session_view, name='terminate_session'),
    path('accounts/privacy/', auth_views.privacy_preferences_view, name='privacy_preferences'),
    path('accounts/delete/', auth_views.delete_account_view, name='delete_account'),
    path('accounts/mfa/setup/', auth_views.mfa_setup_view, name='mfa_setup'),
    path('accounts/mfa/verify/', auth_views.mfa_verify_view, name='mfa_verify'),
    path('accounts/mfa/disable/', auth_views.mfa_disable_view, name='mfa_disable'),
    # Wearable Integrations
    path('wearables/', views.wearable_device_list, name='wearable_device_list'),
    path('wearables/add/', views.wearable_device_add, name='wearable_device_add'),
    path('wearables/edit/<int:pk>/', views.wearable_device_edit, name='wearable_device_edit'),
    path('wearables/delete/<int:pk>/', views.wearable_device_delete, name='wearable_device_delete'),
    path('wearables/connect/<int:pk>/', views.wearable_connect, name='wearable_connect'),
    path('wearables/callback/<str:platform>/', views.wearable_oauth_callback, name='wearable_oauth_callback'),
    path('wearables/disconnect/<int:pk>/', views.wearable_disconnect, name='wearable_disconnect'),
    path('wearables/sync/<int:pk>/', views.wearable_sync, name='wearable_sync'),
    path('wearables/sync-logs/', views.sync_log_list, name='sync_log_list'),

    # Sleep Tracking
    path('sleep/', views.sleep_list, name='sleep_list'),
    path('sleep/add/', views.sleep_add, name='sleep_add'),
    path('sleep/edit/<int:pk>/', views.sleep_edit, name='sleep_edit'),
    path('sleep/delete/<int:pk>/', views.sleep_delete, name='sleep_delete'),

    # Circadian Rhythm
    path('circadian/', views.circadian_list, name='circadian_list'),
    path('circadian/add/', views.circadian_add, name='circadian_add'),
    path('circadian/edit/<int:pk>/', views.circadian_edit, name='circadian_edit'),
    path('circadian/delete/<int:pk>/', views.circadian_delete, name='circadian_delete'),

    # Dream Journal
    path('dreams/', views.dream_list, name='dream_list'),
    path('dreams/add/', views.dream_add, name='dream_add'),
    path('dreams/edit/<int:pk>/', views.dream_edit, name='dream_edit'),
    path('dreams/delete/<int:pk>/', views.dream_delete, name='dream_delete'),

    # Macronutrient Tracking
    path('macros/', views.macro_list, name='macro_list'),
    path('macros/add/', views.macro_add, name='macro_add'),
    path('macros/edit/<int:pk>/', views.macro_edit, name='macro_edit'),
    path('macros/delete/<int:pk>/', views.macro_delete, name='macro_delete'),

    # Micronutrient Tracking
    path('micros/', views.micro_list, name='micro_list'),
    path('micros/add/', views.micro_add, name='micro_add'),
    path('micros/edit/<int:pk>/', views.micro_edit, name='micro_edit'),
    path('micros/delete/<int:pk>/', views.micro_delete, name='micro_delete'),

    # Food Entries
    path('food/', views.food_list, name='food_list'),
    path('food/add/', views.food_add, name='food_add'),
    path('food/edit/<int:pk>/', views.food_edit, name='food_edit'),
    path('food/delete/<int:pk>/', views.food_delete, name='food_delete'),

    # Fasting
    path('fasting/', views.fasting_list, name='fasting_list'),
    path('fasting/add/', views.fasting_add, name='fasting_add'),
    path('fasting/edit/<int:pk>/', views.fasting_edit, name='fasting_edit'),
    path('fasting/delete/<int:pk>/', views.fasting_delete, name='fasting_delete'),

    # Caffeine & Alcohol
    path('caffeine-alcohol/', views.caffeine_alcohol_list, name='caffeine_alcohol_list'),
    path('caffeine-alcohol/add/', views.caffeine_alcohol_add, name='caffeine_alcohol_add'),
    path('caffeine-alcohol/edit/<int:pk>/', views.caffeine_alcohol_edit, name='caffeine_alcohol_edit'),
    path('caffeine-alcohol/delete/<int:pk>/', views.caffeine_alcohol_delete, name='caffeine_alcohol_delete'),

    # User Profiles (RBAC)
    path('profiles/', views.user_profile_list, name='user_profile_list'),
    path('profiles/add/', views.user_profile_add, name='user_profile_add'),
    path('profiles/edit/<int:pk>/', views.user_profile_edit, name='user_profile_edit'),
    path('profiles/delete/<int:pk>/', views.user_profile_delete, name='user_profile_delete'),

    # Family Accounts
    path('family/', views.family_account_list, name='family_account_list'),
    path('family/add/', views.family_account_add, name='family_account_add'),
    path('family/edit/<int:pk>/', views.family_account_edit, name='family_account_edit'),
    path('family/delete/<int:pk>/', views.family_account_delete, name='family_account_delete'),

    # Consent Logs
    path('consent/', views.consent_log_list, name='consent_log_list'),
    path('consent/add/', views.consent_log_add, name='consent_log_add'),
    path('consent/edit/<int:pk>/', views.consent_log_edit, name='consent_log_edit'),
    path('consent/delete/<int:pk>/', views.consent_log_delete, name='consent_log_delete'),

    # Tenant Config
    path('tenants/', views.tenant_config_list, name='tenant_config_list'),
    path('tenants/add/', views.tenant_config_add, name='tenant_config_add'),
    path('tenants/edit/<int:pk>/', views.tenant_config_edit, name='tenant_config_edit'),
    path('tenants/delete/<int:pk>/', views.tenant_config_delete, name='tenant_config_delete'),

    # Admin Telemetry
    path('telemetry/', views.admin_telemetry_list, name='admin_telemetry_list'),
    path('telemetry/add/', views.admin_telemetry_add, name='admin_telemetry_add'),
    path('telemetry/edit/<int:pk>/', views.admin_telemetry_edit, name='admin_telemetry_edit'),
    path('telemetry/delete/<int:pk>/', views.admin_telemetry_delete, name='admin_telemetry_delete'),

    # API Rate Limiting
    path('rate-limits/', views.api_rate_limit_list, name='api_rate_limit_list'),
    path('rate-limits/add/', views.api_rate_limit_add, name='api_rate_limit_add'),
    path('rate-limits/edit/<int:pk>/', views.api_rate_limit_edit, name='api_rate_limit_edit'),
    path('rate-limits/delete/<int:pk>/', views.api_rate_limit_delete, name='api_rate_limit_delete'),

    # Encryption Keys
    path('encryption-keys/', views.encryption_key_list, name='encryption_key_list'),
    path('encryption-keys/add/', views.encryption_key_add, name='encryption_key_add'),
    path('encryption-keys/edit/<int:pk>/', views.encryption_key_edit, name='encryption_key_edit'),
    path('encryption-keys/delete/<int:pk>/', views.encryption_key_delete, name='encryption_key_delete'),

    # Audit Logs
    path('audit-logs/', views.audit_log_list, name='audit_log_list'),
    path('audit-logs/add/', views.audit_log_add, name='audit_log_add'),
    path('audit-logs/edit/<int:pk>/', views.audit_log_edit, name='audit_log_edit'),
    path('audit-logs/delete/<int:pk>/', views.audit_log_delete, name='audit_log_delete'),

    # Anonymized Data Reports
    path('anonymized-data/', views.anonymized_data_list, name='anonymized_data_list'),
    path('anonymized-data/add/', views.anonymized_data_add, name='anonymized_data_add'),
    path('anonymized-data/edit/<int:pk>/', views.anonymized_data_edit, name='anonymized_data_edit'),
    path('anonymized-data/delete/<int:pk>/', views.anonymized_data_delete, name='anonymized_data_delete'),

    # Database Scaling Config
    path('database-scaling/', views.database_scaling_list, name='database_scaling_list'),
    path('database-scaling/add/', views.database_scaling_add, name='database_scaling_add'),
    path('database-scaling/edit/<int:pk>/', views.database_scaling_edit, name='database_scaling_edit'),
    path('database-scaling/delete/<int:pk>/', views.database_scaling_delete, name='database_scaling_delete'),

    # Backup Configuration
    path('backup-config/', views.backup_config_list, name='backup_config_list'),
    path('backup-config/add/', views.backup_config_add, name='backup_config_add'),
    path('backup-config/edit/<int:pk>/', views.backup_config_edit, name='backup_config_edit'),
    path('backup-config/delete/<int:pk>/', views.backup_config_delete, name='backup_config_delete'),

    # Medication Schedule
    path('medications/', views.medication_schedule_list, name='medication_schedule_list'),
    path('medications/add/', views.medication_schedule_add, name='medication_schedule_add'),
    path('medications/edit/<int:pk>/', views.medication_schedule_edit, name='medication_schedule_edit'),
    path('medications/delete/<int:pk>/', views.medication_schedule_delete, name='medication_schedule_delete'),

    # Health Goals
    path('goals/', views.health_goal_list, name='health_goal_list'),
    path('goals/add/', views.health_goal_add, name='health_goal_add'),
    path('goals/edit/<int:pk>/', views.health_goal_edit, name='health_goal_edit'),
    path('goals/delete/<int:pk>/', views.health_goal_delete, name='health_goal_delete'),

    # Critical Alerts
    path('alerts/', views.critical_alert_list, name='critical_alert_list'),
    path('alerts/add/', views.critical_alert_add, name='critical_alert_add'),
    path('alerts/edit/<int:pk>/', views.critical_alert_edit, name='critical_alert_edit'),
    path('alerts/delete/<int:pk>/', views.critical_alert_delete, name='critical_alert_delete'),
    path('alerts/auto-check/', views.critical_alert_auto_check, name='critical_alert_auto_check'),

    # Health Reports
    path('reports/', views.health_report_list, name='health_report_list'),
    path('reports/add/', views.health_report_add, name='health_report_add'),
    path('reports/edit/<int:pk>/', views.health_report_edit, name='health_report_edit'),
    path('reports/delete/<int:pk>/', views.health_report_delete, name='health_report_delete'),
    path('reports/generate/', views.health_report_generate, name='health_report_generate'),

    # Biological Age
    path('bio-age/', views.biological_age_list, name='biological_age_list'),
    path('bio-age/add/', views.biological_age_add, name='biological_age_add'),
    path('bio-age/edit/<int:pk>/', views.biological_age_edit, name='biological_age_edit'),
    path('bio-age/delete/<int:pk>/', views.biological_age_delete, name='biological_age_delete'),
    path('bio-age/estimate/', views.biological_age_estimate, name='biological_age_estimate'),

    # Predictive Biomarkers
    path('biomarkers/', views.predictive_biomarker_list, name='predictive_biomarker_list'),
    path('biomarkers/add/', views.predictive_biomarker_add, name='predictive_biomarker_add'),
    path('biomarkers/edit/<int:pk>/', views.predictive_biomarker_edit, name='predictive_biomarker_edit'),
    path('biomarkers/delete/<int:pk>/', views.predictive_biomarker_delete, name='predictive_biomarker_delete'),
    path('biomarkers/generate/', views.predictive_biomarker_generate, name='predictive_biomarker_generate'),

    # Secure Viewing Links
    path('secure-links/', views.secure_viewing_link_list, name='secure_viewing_link_list'),
    path('secure-links/add/', views.secure_viewing_link_add, name='secure_viewing_link_add'),
    path('secure-links/edit/<int:pk>/', views.secure_viewing_link_edit, name='secure_viewing_link_edit'),
    path('secure-links/delete/<int:pk>/', views.secure_viewing_link_delete, name='secure_viewing_link_delete'),
    path('share/<str:token>/', views.secure_link_shared_view, name='secure_link_shared_view'),

    # Practitioner Access
    path('practitioners/', views.practitioner_access_list, name='practitioner_access_list'),
    path('practitioners/add/', views.practitioner_access_add, name='practitioner_access_add'),
    path('practitioners/edit/<int:pk>/', views.practitioner_access_edit, name='practitioner_access_edit'),
    path('practitioners/delete/<int:pk>/', views.practitioner_access_delete, name='practitioner_access_delete'),
    path('practitioner-portal/', views.practitioner_portal, name='practitioner_portal'),
    path('practitioner-portal/request/', views.practitioner_request_access, name='practitioner_request_access'),

    # Intake Summaries
    path('intake-summaries/', views.intake_summary_list, name='intake_summary_list'),
    path('intake-summaries/add/', views.intake_summary_add, name='intake_summary_add'),
    path('intake-summaries/edit/<int:pk>/', views.intake_summary_edit, name='intake_summary_edit'),
    path('intake-summaries/delete/<int:pk>/', views.intake_summary_delete, name='intake_summary_delete'),
    path('intake-summaries/generate/', views.intake_summary_generate, name='intake_summary_generate'),

    # Data Export
    path('exports/', views.data_export_list, name='data_export_list'),
    path('exports/add/', views.data_export_add, name='data_export_add'),
    path('exports/edit/<int:pk>/', views.data_export_edit, name='data_export_edit'),
    path('exports/delete/<int:pk>/', views.data_export_delete, name='data_export_delete'),
    path('exports/download/<int:pk>/', views.data_export_download, name='data_export_download'),

    # Stakeholder Emails
    path('stakeholder-emails/', views.stakeholder_email_list, name='stakeholder_email_list'),
    path('stakeholder-emails/add/', views.stakeholder_email_add, name='stakeholder_email_add'),
    path('stakeholder-emails/edit/<int:pk>/', views.stakeholder_email_edit, name='stakeholder_email_edit'),
    path('stakeholder-emails/delete/<int:pk>/', views.stakeholder_email_delete, name='stakeholder_email_delete'),
    path('stakeholder-emails/send/<int:pk>/', views.stakeholder_email_send, name='stakeholder_email_send'),

    # Integration Config
    path('integrations/', views.integration_config_list, name='integration_config_list'),
    path('integrations/add/', views.integration_config_add, name='integration_config_add'),
    path('integrations/edit/<int:pk>/', views.integration_config_edit, name='integration_config_edit'),
    path('integrations/delete/<int:pk>/', views.integration_config_delete, name='integration_config_delete'),
    path('integrations/activate/<int:pk>/', views.integration_config_activate, name='integration_config_activate'),
    path('integrations/run/<int:pk>/', views.integration_config_run, name='integration_config_run'),

    # Integration Sub-tasks
    path('subtasks/', views.integration_subtask_list, name='integration_subtask_list'),
    path('subtasks/add/', views.integration_subtask_add, name='integration_subtask_add'),
    path('subtasks/edit/<int:pk>/', views.integration_subtask_edit, name='integration_subtask_edit'),
    path('subtasks/delete/<int:pk>/', views.integration_subtask_delete, name='integration_subtask_delete'),

    # Interoperability Dashboard
    path('phase11/', views.phase11_dashboard, name='phase11_dashboard'),

    # Continuous Monitoring & Alerts
    path('phase12/', views.phase12_dashboard, name='phase12_dashboard'),
    path('monitoring-rules/', views.monitoring_rule_list, name='monitoring_rule_list'),
    path('monitoring-rules/add/', views.monitoring_rule_add, name='monitoring_rule_add'),
    path('monitoring-rules/edit/<int:pk>/', views.monitoring_rule_edit, name='monitoring_rule_edit'),
    path('monitoring-rules/delete/<int:pk>/', views.monitoring_rule_delete, name='monitoring_rule_delete'),
    path('monitoring-events/', views.monitoring_event_list, name='monitoring_event_list'),
    path('monitoring-events/acknowledge/<int:pk>/', views.monitoring_event_acknowledge, name='monitoring_event_acknowledge'),
    path('anomaly-detection/', views.anomaly_detection_list, name='anomaly_detection_list'),
    path('anomaly-detection/run/', views.anomaly_detection_run, name='anomaly_detection_run'),
    path('anomaly-detection/resolve/<int:pk>/', views.anomaly_detection_resolve, name='anomaly_detection_resolve'),
    path('data-pipelines/', views.data_pipeline_list, name='data_pipeline_list'),
    path('data-pipelines/add/', views.data_pipeline_add, name='data_pipeline_add'),
    path('data-pipelines/edit/<int:pk>/', views.data_pipeline_edit, name='data_pipeline_edit'),
    path('data-pipelines/delete/<int:pk>/', views.data_pipeline_delete, name='data_pipeline_delete'),
    path('data-pipelines/run/<int:pk>/', views.data_pipeline_run, name='data_pipeline_run'),
    path('predictive-models/', views.predictive_model_list, name='predictive_model_list'),
    path('predictive-models/add/', views.predictive_model_add, name='predictive_model_add'),
    path('predictive-models/edit/<int:pk>/', views.predictive_model_edit, name='predictive_model_edit'),
    path('predictive-models/delete/<int:pk>/', views.predictive_model_delete, name='predictive_model_delete'),
    path('secure-storage/', views.secure_storage_list, name='secure_storage_list'),
    path('secure-storage/add/', views.secure_storage_add, name='secure_storage_add'),
    path('secure-storage/edit/<int:pk>/', views.secure_storage_edit, name='secure_storage_edit'),
    path('secure-storage/delete/<int:pk>/', views.secure_storage_delete, name='secure_storage_delete'),
    path('export-hub/', views.export_hub, name='export_hub'),
    path('export-hub/generate/', views.export_hub_generate, name='export_hub_generate'),
]
