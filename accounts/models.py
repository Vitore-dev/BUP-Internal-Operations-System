from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('HR', 'HR'),
        ('FINANCE', 'Finance'),
        #('RECEPTION', 'Reception'),
        ('DIRECTOR', 'Director'),
        #('OPS_MANAGER', 'Operations Manager'),
        ('STAFF', 'Staff'),  # Baseline role: any Azure-authenticated user not in an elevated group.
        # No 'PI' role here on purpose — being a Principal Investigator or Study
        # Coordinator is a per-study fact (research.Study.pi / .coordinator),
        # not a system-wide permission tier. A PI's CustomUser.role is just
        # STAFF (or ADMIN/DIRECTOR/etc. if they happen to also hold that).
    ]

    azure_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class EmployeeProfile(models.Model):
    """
    Self-service profile completion: name lives on CustomUser already (first_name/
    last_name), this model just adds what auth doesn't need — the signature image
    used on generated documents like Study Bond letters. One per user, editable by
    the user themselves or by Admin/HR (permission check happens in the view).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile',
    )
    signature_image = models.ImageField(
        upload_to='employee_signatures/',
        null=True,
        blank=True,
        help_text="Upload a scanned signature (PNG with transparent background recommended)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employee Profiles"

    def __str__(self):
        return f"Profile – {self.user.get_full_name() or self.user.username}"

    @property
    def profile_completed(self):
        """
        Computed, not stored — can never drift out of sync with the underlying
        fields. True once the employee has a name and a signature on file.
        """
        return bool(
            self.user.first_name
            and self.user.last_name
            and self.signature_image
        )
