from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    # Employee Directory
    path('directory/', views.employee_directory, name='employee_directory'),

    # Confirmation Letters — HR view (generated letters)
    path('letters/', views.confirmation_letter_list, name='confirmation_letter_list'),
    path('letters/<int:pk>/download/', views.confirmation_letter_download, name='confirmation_letter_download'),

    # Letter Requests — Employee submits, HR completes
    path('letters/request/', views.letter_request_create, name='letter_request_create'),
    path('letters/my-requests/', views.my_letter_requests, name='my_letter_requests'),
    path('letters/requests/', views.letter_request_list, name='letter_request_list'),
    path('letters/requests/<int:pk>/complete/', views.letter_request_complete, name='letter_request_complete'),

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

    #study bond
    path('study-bond/apply/', views.study_bond_request_create, name='study_bond_request_create'),
    path('study-bond/mine/', views.my_study_bond_requests, name='my_study_bond_requests'),
    path('study-bond/queue/', views.study_bond_approval_queue, name='study_bond_approval_queue'),
    path('study-bond/<int:pk>/action/', views.study_bond_action, name='study_bond_action'),
    path('study-bond/<int:pk>/download/', views.study_bond_download, name='study_bond_download'),
 
]


