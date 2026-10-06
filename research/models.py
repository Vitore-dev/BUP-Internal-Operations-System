from django.db import models
from django.conf import settings


class Study(models.Model):
    """
    Deliberately minimal — this is the thin slice of the eventual research app
    built now because two things need it immediately: the employee-facing
    study directory, and Study Bond's approver routing (PI/coordinator).
    No workflow, no compliance fields, no PI profile data — those wait for
    the full research app build-out later.

    pi and coordinator are plain ForeignKeys (not OneToOne / M2M) on purpose:
    a person can be the pi of several studies, or the coordinator of several
    studies, simply by appearing on more than one Study row. Nothing here
    limits either relationship to a single study.
    """

    name = models.CharField(max_length=200)
    short_summary = models.TextField(
        blank=True,
        help_text="Short summary shown to employees in the study directory",
    )

    pi = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='studies_as_pi',
        help_text="The Principal Investigator — owns the study. A study must always have one.",
    )
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='studies_as_coordinator',
        help_text="Manages the study day-to-day, reports to the PI. Can be temporarily unassigned.",
    )
    employees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='studies_as_member',
        help_text="Other staff on this study, distinct from the PI and coordinator.",
    )

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Study"
        verbose_name_plural = "Studies"

    def __str__(self):
        return self.name

    def is_led_by(self, user):
        """True if the given user is this study's PI or coordinator."""
        if not user.is_authenticated:
            return False
        return self.pi_id == user.id or self.coordinator_id == user.id


class PIProfile(models.Model):
    """
    Details for a Principal Investigator who may never sign in.

    A PI who approves by emailed link has no BUP login, so the address the
    link goes to is kept here, separate from the user record's own email
    (which Azure sign-in can overwrite). Changing that address clears the
    "checked" tick, so a corrected address always has to be re-checked
    before any link is sent to it.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pi_profile')
    title = models.CharField(max_length=30, blank=True, help_text="e.g. Dr, Prof")
    phone = models.CharField(max_length=50, blank=True)
    organisation = models.CharField(max_length=200, blank=True)
    approval_email = models.EmailField(help_text="The address approval links are sent to.")
    uses_link = models.BooleanField(
        default=True,
        help_text="Tick if this PI approves by emailed link. Untick for a PI who signs in with a BUP account.",
    )
    email_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pi_emails_checked',
    )
    email_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "PI Profile"
        verbose_name_plural = "PI Profiles"

    def __str__(self):
        return f"PI Profile – {self.display_name}"

    @property
    def display_name(self):
        return f"{self.title} {self.user.get_full_name() or self.user.username}".strip()

    @property
    def email_checked(self):
        return self.email_checked_at is not None

    def save(self, *args, **kwargs):
        self.approval_email = (self.approval_email or '').strip().lower()
        if self.pk:
            previous = PIProfile.objects.filter(pk=self.pk).values_list('approval_email', flat=True).first()
            if previous is not None and previous != self.approval_email:
                self.email_checked_by = None
                self.email_checked_at = None
        super().save(*args, **kwargs)

    def mark_email_checked(self, user):
        from django.utils import timezone
        self.email_checked_by = user
        self.email_checked_at = timezone.now()
        self.save(update_fields=['email_checked_by', 'email_checked_at'])

