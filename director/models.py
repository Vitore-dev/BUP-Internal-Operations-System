from django.db import models
from django.conf import settings
 
 
class DirectorProfile(models.Model):
    """
    Signatory profile for whoever is currently approving Operations-side
    Study Bonds (and later, other Operations approvals). Same pattern as
    hr.HRProfile — keep exactly one is_active=True at a time. When a
    Director is replaced, deactivate the old profile and activate the
    new one; don't delete the old row — past approvals reference it only
    through snapshot fields on StudyBondRequest, not a live FK, so
    deleting it wouldn't break anything but loses your own record of it.
    """
    director_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='director_profile'
    )
    full_name = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200, default="Director")
    organisation = models.CharField(max_length=200, default="Botswana-UPenn Partnership")
    telephone = models.CharField(max_length=50, blank=True)
    signature_image = models.ImageField(
        upload_to='director_signatures/',
        null=True, blank=True,
        help_text="Upload a scanned signature image (PNG with transparent background recommended)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one Director profile should be active at a time"
    )
 
    class Meta:
        verbose_name = "Director Profile"
        verbose_name_plural = "Director Profiles"
 
    def __str__(self):
        return f"Director Profile – {self.full_name}"

