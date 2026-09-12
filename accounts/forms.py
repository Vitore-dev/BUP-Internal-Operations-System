from django import forms
from .models import CustomUser, EmployeeProfile


class NameForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name']


class SignatureForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ['signature_image']
