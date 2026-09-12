from django.contrib import admin
from django.contrib import admin
from .models import HRForm, ConfirmationLetter, ExtracurricularActivity, UserRequest, HRProfile,StudyBondRequest


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

@admin.register(StudyBondRequest)
class StudyBondRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_by', 'department_type', 'status', 'program_title', 'submitted_at')
    list_filter = ('department_type', 'status')
    search_fields = ('requested_by__first_name', 'requested_by__last_name', 'program_title')
    readonly_fields = (
        'hr_reviewed_by', 'hr_reviewed_at',
        'approver_name', 'approver_job_title', 'approver_signature', 'approved_at',
        'verifier_name', 'verifier_job_title', 'verifier_signature', 'verified_at',
    )
 

