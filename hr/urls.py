from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    # Employee Directory
    path('directory/', views.employee_directory, name='employee_directory'),

    # Confirmation Letters
    path('letters/', views.confirmation_letter_list, name='confirmation_letter_list'),
    path('letters/create/', views.confirmation_letter_create, name='confirmation_letter_create'),
    path('letters/<int:pk>/download/', views.confirmation_letter_download, name='confirmation_letter_download'),

    # HR Forms
    path('forms/', views.hr_form_list, name='hr_form_list'),
    path('forms/upload/', views.hr_form_upload, name='hr_form_upload'),
    path('forms/<int:pk>/toggle/', views.hr_form_toggle, name='hr_form_toggle'),
    path('forms/<int:pk>/download/', views.hr_form_download, name='hr_form_download'),

    # Extracurricular Activities
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/create/', views.activity_create, name='activity_create'),
    path('activities/<int:pk>/action/', views.activity_action, name='activity_action'),

    # User Requests
    path('requests/', views.user_request_list, name='user_request_list'),
    path('requests/create/', views.user_request_create, name='user_request_create'),
    path('requests/<int:pk>/action/', views.user_request_action, name='user_request_action'),
]