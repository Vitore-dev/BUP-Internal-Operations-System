from django.contrib import admin
from .models import FinanceSourceFile, FinanceSourceFilePage, FinanceDocument, FinanceDocumentPage, FinanceDocumentVersion


@admin.register(FinanceSourceFile)
class FinanceSourceFileAdmin(admin.ModelAdmin):
    list_display = ('label', 'file', 'page_count', 'uploaded_by', 'uploaded_at')
    search_fields = ('label',)


@admin.register(FinanceDocument)
class FinanceDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at')
    search_fields = ('title',)


@admin.register(FinanceDocumentVersion)
class FinanceDocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'created_by', 'created_at')
    list_filter = ('document',)
