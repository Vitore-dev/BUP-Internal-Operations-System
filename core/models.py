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
