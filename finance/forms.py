from django import forms
from .models import FinanceSourceFile, FinanceDocument


class SourceFileUploadForm(forms.ModelForm):
    class Meta:
        model = FinanceSourceFile
        fields = ['file', 'label']


class DocumentTitleForm(forms.ModelForm):
    class Meta:
        model = FinanceDocument
        fields = ['title']
