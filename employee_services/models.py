from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class StudyBondApplication(models.Model):
    """
    Covers both fresh and continuation Study Bond applications in one table.
    A continuation inherits linked_project, approver, program_title, and
    institution from previous_application rather than re-collecting them —
    same course, same study, same approver, no re-entry.

    Ordering of review matters and is enforced by the status flow, not just
    convention: HR verifies costs and eligibility BEFORE the approver sees
    the application, because the approver needs the real numbers (and the
    "Approval to Register" checklist) to make an informed decision — they
    are not rubber-stamping a number HR already signed off on, they ARE the
    one making the eligibility call, with HR's figures in front of them.
    """

    class ApplicationType(models.TextChoices):
        FRESH = 'FRESH', 'Fresh Application'
        CONTINUATION = 'CONTINUATION', 'Continuation'

    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        PENDING_HR_REVIEW = 'PENDING_HR_REVIEW', 'Pending HR Review'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        DECLINED = 'DECLINED', 'Declined'
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
        COMPLETED = 'COMPLETED', 'Completed'
        RETURNED = 'RETURNED', 'Returned for Changes'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    class GradeStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PASSED = 'PASSED', 'Passed'
        FAILED = 'FAILED', 'Failed'

    # ── Identity & type ──────────────────────────────────────────────
    application_type = models.CharField(max_length=20, choices=ApplicationType.choices)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='study_bond_applications',
    )
    previous_application = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='continuations',
        help_text="Required for a continuation. Fresh applications leave this blank.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)

    # ── Routing (system-determined at submission, not employee-picked) ─
    linked_project = models.ForeignKey(
        'research.Study',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='study_bond_applications',
        help_text=(
            "Which BUP research project the employee is on, used only to "
            "determine the approver. This is NOT the external academic "
            "program being sponsored — see program_title/institution below."
        ),
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='study_bond_approvals',
        help_text="linked_project.pi, unless the applicant IS that PI, or there's no linked_project — then the Director.",
    )

    # ── Employee-submitted: the academic program ────────────────────
    submitted_at = models.DateTimeField(default=timezone.now)
    period_start = models.DateField()
    period_end = models.DateField()
    program_title = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    policy_acknowledged = models.BooleanField(
        default=False,
        help_text="Employee confirms agreement to be bound by the BUP Education Policy.",
    )

    # ── HR verifies (before the approver) ───────────────────────────
    verified_base_pay = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_of_subjects = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Limit 3 subjects per semester — enforced procedurally by HR, not by this field.",
    )
    amount_paid_by_bup = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Must not exceed min(verified_base_pay × 10%, BWP 3000) per fiscal year.",
    )
    hr_notes = models.TextField(blank=True)
    hr_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='study_bond_hr_reviews',
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)

    # ── Approver reviews: the whole "Approval to Register" section ──
    # These five mirror the paper form's checklist exactly. All are the
    # approver's judgment call, made with HR's figures already in hand —
    # none of this is auto-validated by the system.
    program_relevant = models.BooleanField(null=True, blank=True)
    accredited_institution = models.BooleanField(null=True, blank=True)
    good_standing_6_months = models.BooleanField(null=True, blank=True)
    tuition_cap_balance_ok = models.BooleanField(null=True, blank=True)
    supervisor_notified = models.BooleanField(
        null=True, blank=True,
        help_text="Only relevant if the employee is requesting leave to attend classes.",
    )
    decline_reason = models.TextField(blank=True)
    approver_comment = models.TextField(blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)

    # ── Finance processes ────────────────────────────────────────────
    date_of_payment = models.DateField(null=True, blank=True)
    payment_receipt = models.FileField(upload_to='study_bond_receipts/', null=True, blank=True)
    finance_processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='study_bond_payments_processed',
    )
    finance_processed_at = models.DateTimeField(null=True, blank=True)

    # ── Grade verification (exists on every application; HR's job; ──
    # only ever GATES eligibility on a subsequent continuation) ─────
    grade_status = models.CharField(max_length=20, choices=GradeStatus.choices, default=GradeStatus.PENDING)
    grade_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='study_bond_grade_verifications',
    )
    grade_verified_at = models.DateTimeField(null=True, blank=True)
    grade_notes = models.TextField(blank=True)

    # ── Return / withdraw / resubmit / approval by link ────────────
    round_number = models.PositiveIntegerField(
        default=1,
        help_text="1 = first submission. Goes up each time HR returns it and the employee resubmits.",
    )
    approved_by_link = models.BooleanField(
        default=False,
        help_text="True when the approver decided through the emailed one-time link instead of signing in.",
    )
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Study Bond Application"
        verbose_name_plural = "Study Bond Applications"

    def __str__(self):
        return f"{self.get_application_type_display()} – {self.employee} – {self.program_title} ({self.status})"

    def max_allowed_bup_amount(self):
        """
        min(10% of verified base pay, BWP 3000) per fiscal year — the cap
        printed on the paper form. Returns None until HR has entered
        verified_base_pay; this is advisory for the view/template to
        display, not a hard database constraint.
        """
        if self.verified_base_pay is None:
            return None
        return min(self.verified_base_pay * Decimal('0.10'), Decimal('3000'))

    def is_continuation(self):
        return self.application_type == self.ApplicationType.CONTINUATION

    @property
    def current_attachments(self):
        """What reviewers and approvers see: the newest file of each type. Replaced files stay on record."""
        return self.attachments.filter(superseded_at__isnull=True)

    @property
    def superseded_attachments(self):
        return self.attachments.filter(superseded_at__isnull=False)

    @property
    def can_edit(self):
        return self.status == self.Status.RETURNED

    @property
    def can_withdraw(self):
        """Until it is approved. Once Finance has it, money may already be moving."""
        return self.status in (
            self.Status.SUBMITTED, self.Status.PENDING_HR_REVIEW,
            self.Status.RETURNED, self.Status.PENDING_APPROVAL,
        )

    @property
    def latest_return(self):
        return self.returns.order_by('-returned_at').first()


class StudyBondAttachment(models.Model):
    class AttachmentType(models.TextChoices):
        ADMISSION_LETTER = 'ADMISSION_LETTER', 'Admission Letter'
        COURSE_CONTENT = 'COURSE_CONTENT', 'Course Content'
        QUOTATION = 'QUOTATION', 'Course Quotation'
        ACCREDITATION = 'ACCREDITATION', 'Accreditation'
        RESULTS = 'RESULTS', 'Results'
        PREVIOUS_RECEIPT = 'PREVIOUS_RECEIPT', 'Previous Receipt'

    application = models.ForeignKey(
        StudyBondApplication,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    attachment_type = models.CharField(max_length=30, choices=AttachmentType.choices)
    file = models.FileField(upload_to='study_bond_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    superseded_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Set when the employee uploads a newer file of the same type. The old file is kept, not deleted.",
    )

    class Meta:
        ordering = ['attachment_type']

    def __str__(self):
        return f"{self.get_attachment_type_display()} – {self.application}"


class StudyBondReturn(models.Model):
    """
    One round of "HR sent it back". Kept so HR can see, on the review screen,
    what was wrong the last time and when the employee fixed it.
    """
    application = models.ForeignKey(StudyBondApplication, on_delete=models.CASCADE, related_name='returns')
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='study_bond_returns_made',
    )
    returned_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField(help_text="HR's note to the employee. It is emailed to them as written.")
    resubmitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['returned_at']

    def __str__(self):
        return f"Return #{self.pk} of application {self.application_id}"


class ApprovalToken(models.Model):
    """
    A one-time approval link for an approver who does not sign in (a PI).

    Only a hash of the link's secret is stored, never the secret itself, so
    nobody reading the database can reconstruct a working link. A link works
    once, expires, and dies if it is resent, revoked, or the application moves on.
    """
    application = models.ForeignKey(StudyBondApplication, on_delete=models.CASCADE, related_name='approval_tokens')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='approval_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    sent_to = models.CharField(max_length=254, help_text="The address the link was emailed to.")
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    used_ip = models.GenericIPAddressField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Approval link #{self.pk} for application {self.application_id}"
