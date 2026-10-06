from django.contrib import admin
from .models import AuditLog, EmailLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'target_user', 'ip_address', 'description')
    list_filter = ('action',)
    search_fields = ('user__username', 'target_user__username', 'description')
    readonly_fields = ('timestamp', 'user', 'action', 'target_user', 'description', 'ip_address')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'event', 'to_addresses', 'subject')
    list_filter = ('status', 'event')
    search_fields = ('to_addresses', 'intended_to', 'subject')
    readonly_fields = ('event', 'to_addresses', 'intended_to', 'subject', 'body_text', 'status',
                       'error', 'related_id', 'created_at', 'sent_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

