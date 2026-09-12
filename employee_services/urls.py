from django.urls import path
from . import views

app_name = 'employee_services'

urlpatterns = [
    path('', views.portal_home, name='portal_home'),

    # Study directory (read-only)
    path('studies/', views.study_directory, name='study_directory'),

    # Study Bond
    path('study-bond/', views.study_bond_list, name='study_bond_list'),
    path('study-bond/apply/', views.study_bond_apply, name='study_bond_apply'),
    path('study-bond/apply/continuation/', views.study_bond_apply_continuation, name='study_bond_apply_continuation'),
    path('study-bond/<int:pk>/', views.study_bond_detail, name='study_bond_detail'),
    path('study-bond/<int:pk>/verify-grade/', views.study_bond_verify_grade, name='study_bond_verify_grade'),
    path('study-bond/<int:pk>/hr-review/', views.study_bond_hr_review, name='study_bond_hr_review'),
    path('study-bond/<int:pk>/approve/', views.study_bond_approver_review, name='study_bond_approver_review'),
    path('study-bond/<int:pk>/finance/', views.study_bond_finance_process, name='study_bond_finance_process'),
    path('study-bond/<int:pk>/pdf/', views.study_bond_pdf_download, name='study_bond_pdf_download'),
]
