from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, EmployeeProfile


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'department', 'is_archived', 'is_active')
    list_filter = ('role', 'department', 'is_archived', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('BUP Info', {'fields': ('azure_id', 'role', 'department', 'is_archived')}),
    )


admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_complete', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__first_name', 'user__last_name', 'user__username', 'user__email')
    autocomplete_fields = ('user',)

    def profile_complete(self, obj):
        return obj.profile_completed
    profile_complete.boolean = True  # renders as a check/cross icon rather than True/False text
    profile_complete.short_description = "Complete"
