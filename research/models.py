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
