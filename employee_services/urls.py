from django.urls import path
from . import views
from .staff_home import staff_home

app_name = 'employee_services'

urlpatterns = [
    # The landing page. The route name stays 'portal_home' so every existing link to it keeps working.
    path('', staff_home, name='portal_home'),

    # Study directory (read-only)
    path('studies/', views.study_directory, name='study_directory'),

    # Study Bond
    path('study-bond/', views.study_bond_list, name='study_bond_list'),
    path('study-bond/apply/', views.study_bond_apply, name='study_bond_apply'),
    path('study-bond/apply/continuation/', views.study_bond_apply_continuation, name='study_bond_apply_continuation'),

    # Work queues
    path('study-bond/hr-queue/', views.study_bond_hr_queue, name='study_bond_hr_queue'),
    path('study-bond/approver-queue/', views.study_bond_approver_queue, name='study_bond_approver_queue'),
    path('study-bond/finance-queue/', views.study_bond_finance_queue, name='study_bond_finance_queue'),
    path('study-bond/waiting/', views.study_bond_waiting, name='study_bond_waiting'),

    path('study-bond/<int:pk>/', views.study_bond_detail, name='study_bond_detail'),
    path('study-bond/<int:pk>/verify-grade/', views.study_bond_verify_grade, name='study_bond_verify_grade'),
    path('study-bond/<int:pk>/hr-review/', views.study_bond_hr_review, name='study_bond_hr_review'),
    path('study-bond/<int:pk>/approve/', views.study_bond_approver_review, name='study_bond_approver_review'),
    path('study-bond/<int:pk>/finance/', views.study_bond_finance_process, name='study_bond_finance_process'),
    path('study-bond/<int:pk>/pdf/', views.study_bond_pdf_download, name='study_bond_pdf_download'),
    path('study-bond/<int:pk>/edit/', views.study_bond_edit, name='study_bond_edit'),
    path('study-bond/<int:pk>/withdraw/', views.study_bond_withdraw, name='study_bond_withdraw'),
    path('study-bond/<int:pk>/resend-link/', views.study_bond_resend_link, name='study_bond_resend_link'),

    # The approver's emailed link. Public: no sign-in, protected by the link's secret alone.
    path('approval/<str:token>/', views.link_review, name='link_review'),
    path('approval/<str:token>/file/<int:att_id>/', views.link_attachment, name='link_attachment'),
    path('approval-thanks/', views.link_thanks, name='link_thanks'),
]
