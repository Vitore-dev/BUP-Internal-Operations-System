from django.contrib import admin
from .models import StudyBondApplication, StudyBondAttachment


class StudyBondAttachmentInline(admin.TabularInline):
    model = StudyBondAttachment
    extra = 0


@admin.register(StudyBondApplication)
class StudyBondApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'application_type', 'program_title', 'status',
        'approver', 'grade_status', 'submitted_at',
    )
    list_filter = ('application_type', 'status', 'grade_status')
    search_fields = (
        'employee__first_name', 'employee__last_name',
        'program_title', 'institution',
    )
    autocomplete_fields = ('employee', 'approver', 'linked_project', 'previous_application', 'hr_reviewed_by', 'finance_processed_by', 'grade_verified_by')
    readonly_fields = ('submitted_at',)
    inlines = [StudyBondAttachmentInline]

    fieldsets = (
        ('Application', {
            'fields': ('application_type', 'employee', 'previous_application', 'status', 'submitted_at')
        }),
        ('Program details', {
            'fields': ('program_title', 'institution', 'period_start', 'period_end', 'total_cost', 'policy_acknowledged')
        }),
        ('Routing', {
            'fields': ('linked_project', 'approver')
        }),
        ('HR review', {
            'fields': ('verified_base_pay', 'cost_of_subjects', 'amount_paid_by_bup', 'hr_notes', 'hr_reviewed_by', 'hr_reviewed_at')
        }),
        ('Approval to Register', {
            'fields': (
                'program_relevant', 'accredited_institution', 'good_standing_6_months',
                'tuition_cap_balance_ok', 'supervisor_notified',
                'decline_reason', 'approver_comment', 'decision_date',
            )
        }),
        ('Finance', {
            'fields': ('date_of_payment', 'payment_receipt', 'finance_processed_by', 'finance_processed_at')
        }),
        ('Grade verification', {
            'fields': ('grade_status', 'grade_verified_by', 'grade_verified_at', 'grade_notes')
        }),
    )