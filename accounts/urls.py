from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('access-denied/', views.access_denied, name='access_denied'),
]