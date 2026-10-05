from django.urls import path
from .dashboard import director_home

app_name = 'director'

urlpatterns = [
    path('', director_home, name='home'),
]
