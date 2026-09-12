from django.contrib import admin
from .models import Study


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
