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

    # Phase 2: Body Composition
    path('body-composition/', views.body_composition_list, name='body_composition_list'),
    path('body-composition/add/', views.body_composition_add, name='body_composition_add'),
    path('body-composition/edit/<int:pk>/', views.body_composition_edit, name='body_composition_edit'),
    path('body-composition/delete/<int:pk>/', views.body_composition_delete, name='body_composition_delete'),

    # Phase 2: Hydration
    path('hydration/', views.hydration_list, name='hydration_list'),
    path('hydration/add/', views.hydration_add, name='hydration_add'),
    path('hydration/edit/<int:pk>/', views.hydration_edit, name='hydration_edit'),
    path('hydration/delete/<int:pk>/', views.hydration_delete, name='hydration_delete'),

    # Phase 2: Energy & Fatigue
    path('energy/', views.energy_list, name='energy_list'),
    path('energy/add/', views.energy_add, name='energy_add'),
    path('energy/edit/<int:pk>/', views.energy_edit, name='energy_edit'),
    path('energy/delete/<int:pk>/', views.energy_delete, name='energy_delete'),

    # Phase 2: Custom Vitals
    path('custom-vitals/', views.custom_vitals_list, name='custom_vitals_list'),
    path('custom-vitals/define/', views.custom_vital_define, name='custom_vital_define'),
    path('custom-vitals/add/', views.custom_vital_add_entry, name='custom_vital_add_entry'),
    path('custom-vitals/edit/<int:pk>/', views.custom_vital_edit_entry, name='custom_vital_edit_entry'),
    path('custom-vitals/delete/<int:pk>/', views.custom_vital_delete_entry, name='custom_vital_delete_entry'),

    # Phase 2: Pain Mapping
    path('pain/', views.pain_list, name='pain_list'),
    path('pain/add/', views.pain_add, name='pain_add'),
    path('pain/edit/<int:pk>/', views.pain_edit, name='pain_edit'),
    path('pain/delete/<int:pk>/', views.pain_delete, name='pain_delete'),

    # Phase 2: Resting Metabolic Rate
    path('rmr/', views.rmr_list, name='rmr_list'),
    path('rmr/add/', views.rmr_add, name='rmr_add'),
    path('rmr/edit/<int:pk>/', views.rmr_edit, name='rmr_edit'),
    path('rmr/delete/<int:pk>/', views.rmr_delete, name='rmr_delete'),

    # Phase 2: Orthostatic Tracking
    path('orthostatic/', views.orthostatic_list, name='orthostatic_list'),
    path('orthostatic/add/', views.orthostatic_add, name='orthostatic_add'),
    path('orthostatic/edit/<int:pk>/', views.orthostatic_edit, name='orthostatic_edit'),
    path('orthostatic/delete/<int:pk>/', views.orthostatic_delete, name='orthostatic_delete'),

    # Phase 2: Reproductive Health
    path('reproductive/', views.reproductive_list, name='reproductive_list'),
    path('reproductive/add/', views.reproductive_add, name='reproductive_add'),
    path('reproductive/edit/<int:pk>/', views.reproductive_edit, name='reproductive_edit'),
    path('reproductive/delete/<int:pk>/', views.reproductive_delete, name='reproductive_delete'),

    # Phase 2: Symptom Journaling
    path('symptoms/', views.symptom_list, name='symptom_list'),
    path('symptoms/add/', views.symptom_add, name='symptom_add'),
    path('symptoms/edit/<int:pk>/', views.symptom_edit, name='symptom_edit'),
    path('symptoms/delete/<int:pk>/', views.symptom_delete, name='symptom_delete'),

    # Phase 2: Metabolic Monitoring
    path('metabolic/', views.metabolic_list, name='metabolic_list'),
    path('metabolic/add/', views.metabolic_add, name='metabolic_add'),
    path('metabolic/edit/<int:pk>/', views.metabolic_edit, name='metabolic_edit'),
    path('metabolic/delete/<int:pk>/', views.metabolic_delete, name='metabolic_delete'),

    # Phase 2: Ketone Tracking
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

    # Phase 3: Global Search API
    path('api/search/', views.global_search, name='global_search'),

    # Phase 4: User Authentication and Profiles
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
]
