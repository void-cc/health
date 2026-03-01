from django.urls import path
from . import views

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
    path('import/', views.import_data, name='import_data'),
    path('export/', views.export_data, name='export_data'),
]
