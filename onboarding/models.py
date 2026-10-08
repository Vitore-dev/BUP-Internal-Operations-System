import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


class PrivateStorage(FileSystemStorage):
    """Files that must never be reachable by a web address: they live outside MEDIA_ROOT and are handed out only by a view that checks who is asking."""

    def url(self, name):
        raise ValueError('Private files have no public address. Use the download view.')


def get_private_storage():
    root = getattr(settings, 'PRIVATE_MEDIA_ROOT', None) or (settings.BASE_DIR / 'private_media')
    return PrivateStorage(location=str(root))


def upload_path(instance, filename):
    """A random name, so nothing the person typed ever becomes part of a path on the server."""
    ext = os.path.splitext(filename)[1].lower()[:6]
    return f"onboarding/{instance.request_id}/{uuid.uuid4().hex}{ext}"


class PersonalDetailsRequest(models.Model):
    """
    HR sends a new employee, who is not on the system yet, a link to BUP's Personal Details Form.
    This one row holds the invitation and, once the person submits, everything they filled in.
    """

    class Status(models.TextChoices):
        SENT = 'SENT', 'Waiting for the new employee'
        SUBMITTED = 'SUBMITTED', 'Submitted to HR'
        CLOSED = 'CLOSED', 'Closed'

    GENDER_CHOICES = [('FEMALE', 'Female'), ('MALE', 'Male'), ('PREFER_NOT', 'Prefer not to say')]
    MARITAL_CHOICES = [('SINGLE', 'Single'), ('MARRIED', 'Married'), ('DIVORCED', 'Divorced'), ('WIDOWED', 'Widowed'), ('OTHER', 'Other')]

    # Set by HR when sending (the employee checks and can correct the last three)
    recipient_name = models.CharField(max_length=200)
    recipient_email = models.EmailField()
    position_title = models.CharField(max_length=200, blank=True)
    program = models.CharField(max_length=200, blank=True)
    assumption_date = models.DateField(null=True, blank=True, help_text="Date of assumption of duty")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='personal_details_sent')
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SENT)
    status_changed_at = models.DateTimeField(default=timezone.now)
    reopen_note = models.TextField(blank=True)

    # The emailed link. Only a hash of the secret is stored; blank means no link works.
    token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    # What the employee fills in (BUP's Personal Details Form)
    full_names = models.CharField(max_length=200, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=12, blank=True, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=12, blank=True, choices=MARITAL_CHOICES)
    id_number = models.CharField(max_length=40, blank=True, help_text="ID (Omang) or passport number")
    id_expiry = models.DateField(null=True, blank=True)
    postal_address = models.TextField(blank=True)
    physical_address = models.TextField(blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    email_address = models.EmailField(blank=True)
    kin_name = models.CharField(max_length=200, blank=True)
    kin_relationship = models.CharField(max_length=100, blank=True)
    kin_telephone = models.CharField(max_length=30, blank=True)
    emergency_name = models.CharField(max_length=200, blank=True)
    emergency_telephone = models.CharField(max_length=30, blank=True)
    emergency_relationship = models.CharField(max_length=100, blank=True)
    qualifications = models.TextField(blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_branch_code = models.CharField(max_length=20, blank=True)
    bank_branch_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_account_name = models.CharField(max_length=200, blank=True)

    # The declaration at the bottom of the form
    declaration_name = models.CharField(max_length=200, blank=True)
    declaration_ip = models.GenericIPAddressField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient_name} ({self.get_status_display()})"


class PersonalDetailsDocument(models.Model):
    """A scanned document the new employee attached. Kept in private storage."""

    class Kind(models.TextChoices):
        ID_COPY = 'ID_COPY', 'Copy of Passport / Omang'
        HEALTH_CERT = 'HEALTH_CERT', 'Copy of Health Professional Certificate'
        EXEMPTION_CERT = 'EXEMPTION_CERT', 'Copy of exemption certificate'
        QUALIFICATIONS = 'QUALIFICATIONS', 'Certified copies of qualifications'

    request = models.ForeignKey(PersonalDetailsRequest, on_delete=models.CASCADE, related_name='documents')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    file = models.FileField(upload_to=upload_path, storage=get_private_storage)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['kind', 'id']
