from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import AuditLog


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
