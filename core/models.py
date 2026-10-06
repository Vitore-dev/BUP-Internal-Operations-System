from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CHOICES = [
        # Identity
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('USER_ARCHIVED', 'User Archived'),
        ('USER_UNARCHIVED', 'User Unarchived'),
        ('USER_LOGIN', 'User Login'),
        ('USER_LOGOUT', 'User Logout'),
        ('PROFILE_UPDATED', 'Employee Profile Updated'),

        # Study Bond — fresh and continuation applications share these
        ('STUDY_BOND_SUBMITTED', 'Study Bond Submitted'),
        ('STUDY_BOND_HR_REVIEWED', 'Study Bond HR Reviewed'),
        ('STUDY_BOND_APPROVED', 'Study Bond Approved'),
        ('STUDY_BOND_DECLINED', 'Study Bond Declined'),
        ('STUDY_BOND_PAID', 'Study Bond Payment Processed'),
        ('STUDY_BOND_CONTINUATION_SUBMITTED', 'Study Bond Continuation Submitted'),
        ('STUDY_BOND_GRADE_VERIFIED', 'Study Bond Grade Verified'),
        ('STUDY_BOND_RETURNED', 'Study Bond Returned to Employee'),
        ('STUDY_BOND_RESUBMITTED', 'Study Bond Resubmitted'),
        ('STUDY_BOND_WITHDRAWN', 'Study Bond Withdrawn'),
        ('STUDY_BOND_APPROVER_CHANGED', 'Study Bond Approver Changed'),
        ('STUDY_BOND_LINK_SENT', 'Study Bond Approval Link Sent'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='targeted_audit_logs'
    )
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.timestamp} | {self.action} | {self.user}"


class EmailLog(models.Model):
    """
    Every email the system tried to send: who, what, and whether it went.
    A row is written even when email is switched off, so you can review what
    WOULD be sent before turning it on.
    """

    class Status(models.TextChoices):
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'
        SKIPPED = 'SKIPPED', 'Not sent'

    event = models.CharField(max_length=60, blank=True)
    to_addresses = models.TextField()
    intended_to = models.TextField(blank=True, help_text="Who it would have gone to, when test mode redirected it.")
    subject = models.CharField(max_length=255)
    body_text = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SKIPPED)
    error = models.TextField(blank=True)
    related_id = models.PositiveIntegerField(null=True, blank=True, help_text="For Study Bond emails: the application id.")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"{self.created_at:%d %b %Y %H:%M} | {self.status} | {self.subject}"

