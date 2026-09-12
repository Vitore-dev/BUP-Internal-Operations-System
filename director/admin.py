from django.contrib import admin
from .models import DirectorProfile
 
 
@admin.register(DirectorProfile)
class DirectorProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'job_title', 'is_active', 'director_user')
