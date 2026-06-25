from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('admin/', views.admin_dashboard, name='admin'),
    path('hr/', views.hr_dashboard, name='hr'),
    path('finance/', views.finance_dashboard, name='finance'),
    path('reception/', views.reception_dashboard, name='reception'),
    path('director/', views.director_dashboard, name='director'),
    path('ops/', views.ops_dashboard, name='ops'),
    path('pi/', views.pi_dashboard, name='pi'),
]