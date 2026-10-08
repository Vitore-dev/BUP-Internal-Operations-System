from django.contrib import admin

from .models import PersonalDetailsRequest


@admin.register(PersonalDetailsRequest)
class PersonalDetailsRequestAdmin(admin.ModelAdmin):
    """
    Deliberately thin. IT admins can see that a form exists and its status, but NOT the ID or passport
    number or any bank detail: those are shown only to HR, on HR's own page, where every view is recorded.
    """
    list_display = ('recipient_name', 'recipient_email', 'status', 'created_at', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('recipient_name', 'recipient_email')
    exclude = ('id_number', 'id_expiry', 'bank_name', 'bank_branch_code', 'bank_branch_name', 'bank_account_number', 'bank_account_name',
               'date_of_birth', 'postal_address', 'physical_address', 'telephone', 'kin_name', 'kin_relationship', 'kin_telephone',
               'emergency_name', 'emergency_telephone', 'emergency_relationship', 'gender', 'marital_status', 'qualifications',
               'email_address', 'token_hash')
    readonly_fields = ('recipient_name', 'recipient_email', 'created_by', 'created_at', 'status', 'status_changed_at', 'submitted_at',
                       'declaration_ip', 'last_used_at', 'token_expires_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
