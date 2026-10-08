from django.urls import path
from . import views
from . import document_delete
from .dashboard import finance_home

app_name = 'finance'

urlpatterns = [
    path('', finance_home, name='home'),
    path('documents/', views.document_list, name='document_list'),
    path('documents/new/', views.document_create, name='document_create'),
    path('documents/<int:pk>/builder/', views.document_builder, name='document_builder'),
    path('documents/<int:pk>/upload-source/', views.document_upload_source, name='document_upload_source'),
    path('documents/<int:pk>/save-composition/', views.document_save_composition, name='document_save_composition'),
    path('documents/<int:pk>/versions/', views.document_versions, name='document_versions'),
    path('documents/<int:pk>/versions/<int:version_pk>/delete/', views.document_version_delete, name='document_version_delete'),
    path('documents/<int:pk>/delete/', document_delete.document_delete, name='document_delete'),
]