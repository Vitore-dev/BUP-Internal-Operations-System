import os
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import models
from django.db import models
from django.conf import settings
from director.models import DirectorProfile

class LetterRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending HR Review'),
        ('COMPLETED', 'Completed'),
        ('DECLINED', 'Declined'),
    ]
    SALUTATION_CHOICES = [
        ('Mr.', 'Mr.'),
        ('Mrs.', 'Mrs.'),
        ('Ms.', 'Ms.'),
        ('Dr.', 'Dr.'),
        ('Prof.', 'Prof.'),
    ]

    # Filled by the employee
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='letter_requests'
    )
    salutation = models.CharField(max_length=10, choices=SALUTATION_CHOICES)
    employee_id_number = models.CharField(max_length=50, blank=True)
    job_title = models.CharField(max_length=200)
    plot_number = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    po_box = models.CharField(max_length=100, blank=True)
    postal_city = models.CharField(max_length=100, blank=True, default='Gaborone')
    purpose = models.CharField(max_length=200, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)

    # Filled by HR
    annual_salary = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    hr_notes = models.TextField(blank=True)
    actioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='letter_requests_actioned'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    actioned_at = models.DateTimeField(null=True, blank=True)

    # Generated letter (linked after HR completes it)
    confirmation_letter = models.OneToOneField(
        'ConfirmationLetter',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='letter_request'
    )

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Letter Request – {self.requested_by.get_full_name()} – {self.status}"

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



# SECTION 1 — add to hr/models.py
# ----------------------------------------------------------------
# Add these imports at the top of models.py if not already present:
#
#   import os
#   from django.core.files.base import ContentFile
#   from django.utils import timezone
#
# Then append:
 

 
 
def _snapshot_signature(source_field, prefix):
    """
    Copies an approver's CURRENT signature image into a new file at
    approval time, so a later change to their profile (new signature,
    replaced Director, changed job title) never retroactively alters
    a document that was already signed. Returns a ContentFile, or None
    if the source has no image.
    """
    if not source_field:
        return None
    source_field.open('rb')
    data = source_field.read()
    source_field.close()
    ext = os.path.splitext(source_field.name)[1] or '.png'
    return ContentFile(data, name=f"{prefix}{ext}")
 
 
class StudyBondRequest(models.Model):
    DEPARTMENT_TYPE_CHOICES = [
        ('OPERATIONS', 'Operations'),
        ('RESEARCH', 'Research / Studies'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval to Register'),
        ('PENDING_HR_REVIEW', 'Pending HR Review'),
        ('REGISTERED', 'Approved to Register'),
        ('DECLINED', 'Declined'),
        ('COMPLETED', 'Completed – Grade Verified'),
    ]
 
    # ── Filled by employee ──────────────────────────────────────
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='study_bond_requests'
    )
    department_type = models.CharField(max_length=20, choices=DEPARTMENT_TYPE_CHOICES)
 
    # RESEARCH only. No employee → PI mapping exists yet anywhere in the
    # system, so for now the requester picks the responsible PI manually
    # at submission time. Once a real mapping exists (e.g. a PI field on
    # CustomUser, or a Project model), swap this for an auto-assignment
    # the same way OPERATIONS auto-assigns to the active Director.
    assigned_pi = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='study_bonds_as_pi',
        limit_choices_to={'role': 'PI'},
    )
 
    period_start = models.DateField()
    period_end = models.DateField()
    program_title = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    subject_costs = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Cost of subjects, limit 3 per semester"
    )
    amount_paid_by_bup = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(null=True, blank=True)
    payment_receipt = models.FileField(upload_to='study_bond_receipts/', null=True, blank=True)
 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)
 
    # ── Stage 1: Approval to Register (snapshotted at approval time) ──
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='study_bonds_registered'
    )
    approver_name = models.CharField(max_length=200, blank=True)
    approver_job_title = models.CharField(max_length=200, blank=True)
    approver_signature = models.ImageField(upload_to='study_bond_signatures/', null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)
 
    # ── Stage 2: HR Review — runs AFTER Director/PI approval, not before.
    #     HR is the source of truth for salary (same as ConfirmationLetter/
    #     LetterRequest), and confirms the real cap as the final step
    #     before a bond counts as registered — HR only has to do this for
    #     requests that already cleared the eligibility check. ──
    hr_verified_salary = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Employee's verified annual base pay"
    )
    hr_cap_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Confirmed cap: 10% of base pay or BWP 3000/yr equivalent, whichever is less"
    )
    hr_notes = models.TextField(blank=True)
    hr_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='study_bonds_hr_reviewed'
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)
 
    # ── Stage 3: Grade Verification — happens later, possibly by a
    #     different person than whoever approved registration, so it
    #     gets its own independent snapshot rather than reusing stage 1 ──
    grade_received = models.CharField(max_length=50, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='study_bonds_grade_verified'
    )
    verifier_name = models.CharField(max_length=200, blank=True)
    verifier_job_title = models.CharField(max_length=200, blank=True)
    verifier_signature = models.ImageField(upload_to='study_bond_signatures/', null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
 
    class Meta:
        ordering = ['-submitted_at']
 
    def __str__(self):
        return f"Study Bond – {self.requested_by.get_full_name()} – {self.status}"
 
    # ── Routing / permissions ───────────────────────────────────
    def get_pending_approver_user(self):
        """Who should act next, or None. Used for display, not enforcement."""
        if self.department_type == 'OPERATIONS':
            director = DirectorProfile.objects.filter(is_active=True).select_related('director_user').first()
            return director.director_user if director else None
        if self.department_type == 'RESEARCH':
            return self.assigned_pi
        return None
 
    def can_be_actioned_by(self, user):
        if user.role == 'ADMIN':
            return True
        if self.status == 'PENDING_HR_REVIEW':
            return user.role == 'HR'
        if self.status in ('PENDING', 'REGISTERED'):
            # PENDING = approve/decline-to-register; REGISTERED = grade
            # verification — same responsible approver handles both.
            if self.department_type == 'OPERATIONS' and user.role == 'DIRECTOR':
                return DirectorProfile.objects.filter(is_active=True, director_user=user).exists()
            if self.department_type == 'RESEARCH' and user.role == 'PI':
                return self.assigned_pi_id == user.id
        return False
 
    def _resolve_signature_source(self, user):
        """Returns (name, job_title, signature_image_field_or_None) for the acting user."""
        if user.role == 'DIRECTOR':
            profile = DirectorProfile.objects.filter(director_user=user).first()
            if profile:
                return profile.full_name, profile.job_title, profile.signature_image
        if user.role == 'PI':
            # No PIProfile yet — falls back to the account name with no
            # signature image. Swap this branch out once PIProfile exists
            # for Research, same shape as DirectorProfile.
            return user.get_full_name() or user.username, 'Project Coordinator', None
        return user.get_full_name() or user.username, 'Admin', None
 
    # ── State transitions ───────────────────────────────────────
    def approve_registration(self, user):
        """Director/PI clears eligibility. Doesn't finalize the bond —
        hands off to HR to confirm the numbers, which is the last step."""
        name, title, sig_field = self._resolve_signature_source(user)
        self.status = 'PENDING_HR_REVIEW'
        self.approved_by = user
        self.approver_name = name
        self.approver_job_title = title
        snap = _snapshot_signature(sig_field, f"studybond_{self.pk}_reg")
        if snap:
            self.approver_signature.save(snap.name, snap, save=False)
        self.approved_at = timezone.now()
        self.save()
 
    def decline_registration(self, user, reason=''):
        self.status = 'DECLINED'
        self.approved_by = user
        self.decline_reason = reason
        self.approved_at = timezone.now()
        self.save()
 
    def hr_review_forward(self, user, salary, cap_amount, notes=''):
        """HR is the last one to fill in details — this is what actually
        finalizes the bond as registered."""
        self.hr_verified_salary = salary
        self.hr_cap_amount = cap_amount
        self.hr_notes = notes
        self.hr_reviewed_by = user
        self.hr_reviewed_at = timezone.now()
        self.status = 'REGISTERED'
        self.save()
 
    def hr_review_decline(self, user, notes=''):
        self.hr_notes = notes
        self.hr_reviewed_by = user
        self.hr_reviewed_at = timezone.now()
        self.decline_reason = notes
        self.status = 'DECLINED'
        self.save()
 
    def verify_grade(self, user, grade):
        name, title, sig_field = self._resolve_signature_source(user)
        self.status = 'COMPLETED'
        self.grade_received = grade
        self.verified_by = user
        self.verifier_name = name
        self.verifier_job_title = title
        snap = _snapshot_signature(sig_field, f"studybond_{self.pk}_grade")
        if snap:
            self.verifier_signature.save(snap.name, snap, save=False)
        self.verified_at = timezone.now()
        self.save()
 