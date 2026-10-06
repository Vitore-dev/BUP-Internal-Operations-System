from django.contrib import admin
from .models import ApprovalToken, StudyBondApplication, StudyBondAttachment, StudyBondReturn


class StudyBondAttachmentInline(admin.TabularInline):
    model = StudyBondAttachment
    extra = 0


class StudyBondReturnInline(admin.TabularInline):
    model = StudyBondReturn
    extra = 0
    readonly_fields = ('returned_by', 'returned_at', 'reason', 'resubmitted_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(StudyBondApplication)
class StudyBondApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'application_type', 'program_title', 'status', 'round_number',
        'approver', 'grade_status', 'submitted_at',
    )
    list_filter = ('application_type', 'status', 'grade_status')
    search_fields = (
        'employee__first_name', 'employee__last_name',
        'program_title', 'institution',
    )
    autocomplete_fields = ('employee', 'approver', 'linked_project', 'previous_application', 'hr_reviewed_by', 'finance_processed_by', 'grade_verified_by')
    readonly_fields = ('submitted_at',)
    inlines = [StudyBondAttachmentInline, StudyBondReturnInline]

    fieldsets = (
        ('Application', {
            'fields': ('application_type', 'employee', 'previous_application', 'status', 'round_number', 'submitted_at')
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
                'decline_reason', 'approver_comment', 'decision_date', 'approved_by_link',
            )
        }),
        ('Finance', {
            'fields': ('date_of_payment', 'payment_receipt', 'finance_processed_by', 'finance_processed_at')
        }),
        ('Grade verification', {
            'fields': ('grade_status', 'grade_verified_by', 'grade_verified_at', 'grade_notes')
        }),
        ('Withdrawal', {
            'fields': ('withdrawn_at', 'withdrawn_reason')
        }),
    )


@admin.register(ApprovalToken)
class ApprovalTokenAdmin(admin.ModelAdmin):
    """Read-only record of approval links. The secret itself is never stored, only its hash."""
    list_display = ('application', 'approver', 'sent_to', 'created_at', 'expires_at', 'used_at', 'revoked_at')
    list_filter = ('used_at', 'revoked_at')
    search_fields = ('sent_to', 'application__program_title')
    readonly_fields = ('application', 'approver', 'token_hash', 'sent_to', 'created_at', 'expires_at',
                       'used_at', 'used_ip', 'revoked_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
