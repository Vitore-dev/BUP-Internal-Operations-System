from django.contrib import admin
from .models import Study, PIProfile


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ('name', 'pi', 'coordinator', 'employee_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'pi__first_name', 'pi__last_name', 'coordinator__first_name', 'coordinator__last_name')
    autocomplete_fields = ('pi', 'coordinator', 'employees')
    filter_horizontal = ('employees',)

    def employee_count(self, obj):
        return obj.employees.count()
    employee_count.short_description = 'Members'


@admin.register(PIProfile)
class PIProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'approval_email', 'uses_link', 'email_is_checked')
    list_filter = ('uses_link',)
    search_fields = ('user__first_name', 'user__last_name', 'approval_email')
    autocomplete_fields = ('user',)
    readonly_fields = ('email_checked_by', 'email_checked_at')
    actions = ['mark_checked']

    def email_is_checked(self, obj):
        return obj.email_checked
    email_is_checked.boolean = True
    email_is_checked.short_description = "Email checked"

    @admin.action(description="Mark the selected approval emails as checked")
    def mark_checked(self, request, queryset):
        for profile in queryset:
            profile.mark_email_checked(request.user)
        self.message_user(request, f"{queryset.count()} approval email(s) marked as checked.")
