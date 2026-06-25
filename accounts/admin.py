from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'department', 'is_archived', 'is_active')
    list_filter = ('role', 'department', 'is_archived', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('BUP Info', {'fields': ('azure_id', 'role', 'department', 'is_archived')}),
    )


admin.site.register(CustomUser, CustomUserAdmin)
