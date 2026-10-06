from django import forms
from django.utils import timezone

from .models import StudyBondApplication, StudyBondAttachment
from .routing import candidate_approvers, studies_for


class OwnStudiesMixin:
    """
    The study dropdown only lists studies the employee is actually on, so an
    employee can never steer an application to someone else's PI. With no studies
    there is no dropdown at all and the application goes to the Director.
    """
    def limit_studies_to(self, employee):
        if employee is None:
            return
        studies = studies_for(employee)
        if studies.exists():
            field = self.fields['linked_project']
            field.queryset = studies
            field.empty_label = "None of these (goes to the Director)"
        else:
            del self.fields['linked_project']


class StudyBondApplicationForm(OwnStudiesMixin, forms.ModelForm):
    """Fresh application — the employee-filled fields only."""

    policy_acknowledged = forms.BooleanField(
        required=True,
        label="I agree to be bound by the terms of the BUP Education Policy",
    )

    class Meta:
        model = StudyBondApplication
        fields = [
            'linked_project', 'period_start', 'period_end',
            'program_title', 'institution', 'total_cost',
            'policy_acknowledged',
        ]
        widgets = {
            'period_start': forms.DateInput(attrs={'type': 'date'}),
            'period_end': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'linked_project': "Research study this application is under",
        }
        help_texts = {
            'linked_project': "Only studies you are on are listed. The study's PI will approve it. "
                              "Choose none to send it to the Director.",
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.limit_studies_to(employee)


class StudyBondEditForm(OwnStudiesMixin, forms.ModelForm):
    """The same employee-filled fields, used when HR has returned an application for changes."""

    class Meta:
        model = StudyBondApplication
        fields = ['linked_project', 'period_start', 'period_end', 'program_title', 'institution', 'total_cost']
        widgets = {
            'period_start': forms.DateInput(attrs={'type': 'date'}),
            'period_end': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'linked_project': "Research study this application is under",
        }
        help_texts = {
            'linked_project': "Only studies you are on are listed. Choose none to send it to the Director.",
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.limit_studies_to(employee)


class StudyBondFreshAttachmentsForm(forms.Form):
    admission_letter = forms.FileField(required=True, label="Admission Letter")
    course_content = forms.FileField(required=True, label="Course Content")
    quotation = forms.FileField(required=True, label="Course Quotation")
    accreditation = forms.FileField(required=True, label="Accreditation")

    FIELD_TO_TYPE = {
        'admission_letter': StudyBondAttachment.AttachmentType.ADMISSION_LETTER,
        'course_content': StudyBondAttachment.AttachmentType.COURSE_CONTENT,
        'quotation': StudyBondAttachment.AttachmentType.QUOTATION,
        'accreditation': StudyBondAttachment.AttachmentType.ACCREDITATION,
    }

    def save(self, application):
        for field_name, attachment_type in self.FIELD_TO_TYPE.items():
            uploaded = self.cleaned_data.get(field_name)
            if uploaded:
                StudyBondAttachment.objects.create(
                    application=application,
                    attachment_type=attachment_type,
                    file=uploaded,
                )


class EditAttachmentsForm(forms.Form):
    """
    Used when an application has been returned. Every file is optional: upload only
    what needs replacing. A replaced file is kept on record but no longer shown to reviewers.
    """
    admission_letter = forms.FileField(required=False, label="Admission Letter")
    course_content = forms.FileField(required=False, label="Course Content")
    quotation = forms.FileField(required=False, label="Course Quotation")
    accreditation = forms.FileField(required=False, label="Accreditation")
    results = forms.FileField(required=False, label="Results")
    previous_receipt = forms.FileField(required=False, label="Previous Receipt")

    FIELD_TO_TYPE = {
        'admission_letter': StudyBondAttachment.AttachmentType.ADMISSION_LETTER,
        'course_content': StudyBondAttachment.AttachmentType.COURSE_CONTENT,
        'quotation': StudyBondAttachment.AttachmentType.QUOTATION,
        'accreditation': StudyBondAttachment.AttachmentType.ACCREDITATION,
        'results': StudyBondAttachment.AttachmentType.RESULTS,
        'previous_receipt': StudyBondAttachment.AttachmentType.PREVIOUS_RECEIPT,
    }
    FRESH_FIELDS = ('admission_letter', 'course_content', 'quotation', 'accreditation')
    CONTINUATION_FIELDS = ('results', 'previous_receipt', 'course_content', 'quotation', 'accreditation')

    def __init__(self, *args, application=None, **kwargs):
        super().__init__(*args, **kwargs)
        keep = self.CONTINUATION_FIELDS if (application and application.is_continuation()) else self.FRESH_FIELDS
        for name in list(self.fields):
            if name not in keep:
                del self.fields[name]

    def save(self, application):
        now = timezone.now()
        for field_name, attachment_type in self.FIELD_TO_TYPE.items():
            uploaded = self.cleaned_data.get(field_name)
            if uploaded:
                application.attachments.filter(
                    attachment_type=attachment_type, superseded_at__isnull=True,
                ).update(superseded_at=now)
                StudyBondAttachment.objects.create(
                    application=application,
                    attachment_type=attachment_type,
                    file=uploaded,
                )


class ContinuationRequestForm(forms.Form):
    """
    Picks which prior application this continues. Everything else
    (linked_project, approver, program_title, institution) is copied
    from that record in the view — never re-entered.
    """
    previous_application = forms.ModelChoiceField(
        queryset=StudyBondApplication.objects.none(),
        label="Which application is this continuing?",
    )
    policy_acknowledged = forms.BooleanField(
        required=True,
        label="I agree to be bound by the terms of the BUP Education Policy",
    )

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        if employee is not None:
            S = StudyBondApplication.Status
            self.fields['previous_application'].queryset = (
                StudyBondApplication.objects.filter(employee=employee)
                .exclude(status__in=[S.DECLINED, S.WITHDRAWN, S.RETURNED])
            )


class ContinuationAttachmentsForm(forms.Form):
    results = forms.FileField(required=True, label="Results")
    previous_receipt = forms.FileField(required=True, label="Previous Receipt")
    course_content = forms.FileField(required=False, label="Course Content (if updated)")
    quotation = forms.FileField(required=False, label="Course Quotation (if updated)")
    accreditation = forms.FileField(required=False, label="Accreditation (if updated)")

    FIELD_TO_TYPE = {
        'results': StudyBondAttachment.AttachmentType.RESULTS,
        'previous_receipt': StudyBondAttachment.AttachmentType.PREVIOUS_RECEIPT,
        'course_content': StudyBondAttachment.AttachmentType.COURSE_CONTENT,
        'quotation': StudyBondAttachment.AttachmentType.QUOTATION,
        'accreditation': StudyBondAttachment.AttachmentType.ACCREDITATION,
    }

    def save(self, application):
        for field_name, attachment_type in self.FIELD_TO_TYPE.items():
            uploaded = self.cleaned_data.get(field_name)
            if uploaded:
                StudyBondAttachment.objects.create(
                    application=application,
                    attachment_type=attachment_type,
                    file=uploaded,
                )


class GradeVerificationForm(forms.Form):
    """
    Used on the PREVIOUS application when a continuation is filed against
    it. This is what gates the continuation — not filled on the
    continuation itself.
    """
    grade_status = forms.ChoiceField(
        choices=[
            (StudyBondApplication.GradeStatus.PASSED, 'Passed'),
            (StudyBondApplication.GradeStatus.FAILED, 'Failed'),
        ],
        widget=forms.RadioSelect,
    )
    grade_notes = forms.CharField(widget=forms.Textarea, required=False)


class HRReviewForm(forms.ModelForm):
    """
    HR verifies costs only. The five eligibility checkboxes on the paper
    form ("Approval to Register") belong to the approver, not HR — see
    ApproverReviewForm.
    """
    class Meta:
        model = StudyBondApplication
        fields = ['verified_base_pay', 'cost_of_subjects', 'amount_paid_by_bup', 'hr_notes']
        widgets = {'hr_notes': forms.Textarea(attrs={'rows': 3})}


class ReturnForm(forms.Form):
    """HR sends an application back to the employee. The reason is emailed to them as written."""
    reason = forms.CharField(
        label="What needs to change",
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="The employee receives this by email, exactly as you write it here.",
    )


class ChangeApproverForm(forms.Form):
    approver = forms.ChoiceField(label="Send this application to")

    def __init__(self, *args, application=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = candidate_approvers(application)
        self.fields['approver'].choices = choices
        current = None
        if application.linked_project_id and application.linked_project.pi_id == application.approver_id:
            current = f"study:{application.linked_project_id}"
        if current in dict(choices):
            self.fields['approver'].initial = current


class WithdrawForm(forms.Form):
    reason = forms.CharField(
        required=False, label="Reason (optional)",
        widget=forms.Textarea(attrs={'rows': 3}),
    )


class ApproverReviewForm(forms.ModelForm):
    DECISION_CHOICES = [('APPROVED', 'Approve'), ('DECLINED', 'Decline')]

    decision = forms.ChoiceField(choices=DECISION_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = StudyBondApplication
        fields = [
            'program_relevant', 'accredited_institution', 'good_standing_6_months',
            'tuition_cap_balance_ok', 'supervisor_notified',
            'approver_comment', 'decline_reason',
        ]
        widgets = {
            'approver_comment': forms.Textarea(attrs={'rows': 3}),
            'decline_reason': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('decision') == 'DECLINED' and not cleaned.get('decline_reason'):
            self.add_error('decline_reason', "Required when declining.")
        return cleaned


class FinanceProcessForm(forms.ModelForm):
    class Meta:
        model = StudyBondApplication
        fields = ['date_of_payment', 'payment_receipt']
        widgets = {'date_of_payment': forms.DateInput(attrs={'type': 'date'})}
