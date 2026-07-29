from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import HRForm, ConfirmationLetter, ExtracurricularActivity, UserRequest, HRProfile


@admin.register(HRProfile)
class HRProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'job_title', 'telephone', 'is_active')


@admin.register(ConfirmationLetter)
class ConfirmationLetterAdmin(admin.ModelAdmin):
    list_display = ('employee', 'salutation', 'job_title', 'date_issued', 'created_by')
    list_filter = ('date_issued',)
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(HRForm)
class HRFormAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at', 'uploaded_by')


@admin.register(ExtracurricularActivity)
class ExtracurricularActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'proposed_date', 'status', 'submitted_by')
    list_filter = ('status',)


@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ('request_type', 'employee_name', 'status', 'submitted_by', 'created_at')
    list_filter = ('request_type', 'status')
