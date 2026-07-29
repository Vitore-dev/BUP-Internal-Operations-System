from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

class HRProfile(models.Model):
    """
    Stores the HR officer's signature and contact details
    used on confirmation letters. Only one active profile at a time.
    """
    hr_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hr_profile'
    )
    full_name = models.CharField(
        max_length=200,
        help_text="Full name as it appears on letters e.g. Lindiwe Maidi"
    )
    job_title = models.CharField(
        max_length=200,
        default="Human Resources Coordinator"
    )
    organisation = models.CharField(
        max_length=200,
        default="Botswana-UPenn Partnership"
    )
    telephone = models.CharField(max_length=50, blank=True, help_text="e.g. 3554855")
    signature_image = models.ImageField(
        upload_to='hr_signatures/',
        null=True,
        blank=True,
        help_text="Upload a scanned signature image (PNG with transparent background recommended)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one HR profile should be active at a time"
    )

    class Meta:
        verbose_name = "HR Profile"
        verbose_name_plural = "HR Profiles"

    def __str__(self):
        return f"HR Profile – {self.full_name}"


class HRForm(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='hr_forms/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='hr_forms'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ConfirmationLetter(models.Model):
    SALUTATION_CHOICES = [
        ('Mr.', 'Mr.'),
        ('Mrs.', 'Mrs.'),
        ('Ms.', 'Ms.'),
        ('Dr.', 'Dr.'),
        ('Prof.', 'Prof.'),
    ]

    # Who the letter is for
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='confirmation_letters'
    )
    salutation = models.CharField(
        max_length=10,
        choices=SALUTATION_CHOICES,
        default='Ms.'
    )
    employee_id_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Employee's national ID or staff ID number"
    )
    job_title = models.CharField(
        max_length=200,
        help_text="e.g. Research Assistant, Finance Officer"
    )
    annual_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual salary in BWP"
    )

    # Physical address
    plot_number = models.CharField(max_length=100, blank=True, help_text="e.g. 1234")
    ward = models.CharField(max_length=100, blank=True, help_text="e.g. Tlokweng")

    # Postal address
    po_box = models.CharField(max_length=100, blank=True, help_text="e.g. PO Box 1234")
    postal_city = models.CharField(max_length=100, blank=True, default="Gaborone")

    # Letter metadata
    purpose = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. Bank confirmation, Visa application"
    )
    date_issued = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='letters_created'
    )
    pdf_file = models.FileField(
        upload_to='confirmation_letters/',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-date_issued']

    def __str__(self):
        return f"Confirmation Letter – {self.salutation} {self.employee.get_full_name()} – {self.date_issued}"

    def get_full_address_physical(self):
        parts = []
        if self.plot_number:
            parts.append(f"Plot {self.plot_number}")
        if self.ward:
            parts.append(f"{self.ward} Ward")
        return ", ".join(parts) if parts else "—"

    def get_full_address_postal(self):
        return self.po_box if self.po_box else "—"

class ExtracurricularActivity(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('DECLINED', 'Declined'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    proposed_date = models.DateField()
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='activities_submitted'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    director_comment = models.TextField(blank=True)
    actioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activities_actioned'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Extracurricular Activities'

    def __str__(self):
        return f"{self.title} ({self.status})"


class UserRequest(models.Model):
    REQUEST_TYPE_CHOICES = [
        ('ADD', 'Add User'),
        ('REMOVE', 'Remove User'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIONED', 'Actioned'),
        ('DECLINED', 'Declined'),
    ]

    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES)
    employee_name = models.CharField(max_length=200)
    employee_email = models.EmailField()
    department = models.CharField(max_length=100, blank=True)
    reason = models.TextField()
    last_working_date = models.DateField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='user_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_type} - {self.employee_name} ({self.status})"
