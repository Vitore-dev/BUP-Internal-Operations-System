from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('access-denied/', views.access_denied, name='access_denied'),
    path('profile/', views.profile, name='profile'),
    path('profile/<int:user_id>/edit/', views.admin_edit_profile, name='admin_edit_profile'),
]