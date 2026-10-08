from django.urls import path

from . import hr_views, views

app_name = 'onboarding'

urlpatterns = [
    # HR
    path('', hr_views.hr_list, name='hr_list'),
    path('new/', hr_views.hr_new, name='hr_new'),
    path('<int:pk>/', hr_views.hr_detail, name='hr_detail'),
    path('<int:pk>/action/', hr_views.hr_action, name='hr_action'),
    path('<int:pk>/pdf/', hr_views.hr_pdf, name='hr_pdf'),
    path('<int:pk>/document/<int:doc_pk>/', hr_views.hr_document, name='hr_document'),
    path('<int:pk>/delete/', hr_views.hr_delete, name='hr_delete'),

    # The new employee: a private emailed link, no sign-in.
    path('f/<str:token>/', views.form, name='form'),
    path('thanks/', views.thanks, name='thanks'),
]
