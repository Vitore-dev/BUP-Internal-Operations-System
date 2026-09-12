from django import forms
from .models import StudyBondApplication, StudyBondAttachment


class StudyBondApplicationForm(forms.ModelForm):
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
            'linked_project': "BUP research project you're on (if any)",
        }
        help_texts = {
            'linked_project': "Leave blank if you're not on a research project — your application will route to the Director.",
        }


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
            self.fields['previous_application'].queryset = (
                StudyBondApplication.objects.filter(employee=employee)
                .exclude(status=StudyBondApplication.Status.DECLINED)
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
