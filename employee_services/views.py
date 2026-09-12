from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q

from core.utils import log_action
from core.notifications import notify
from research.models import Study
from .models import StudyBondApplication, StudyBondAttachment
from .forms import (
    StudyBondApplicationForm, StudyBondFreshAttachmentsForm,
    ContinuationRequestForm, ContinuationAttachmentsForm, GradeVerificationForm,
    HRReviewForm, ApproverReviewForm, FinanceProcessForm,
)
from .decorators import (
    owner_or_admin_hr_required, hr_review_required,
    approver_required, finance_required,
)


def determine_approver(employee, linked_project):
    """
    The routing rule, in one place:
    - No linked_project (Operations staff, or research staff not on a
      specific project) -> Director approves.
    - Employee IS the linked_project's PI -> Director approves (nobody
      sits above a PI on their own project).
    - Otherwise -> the linked_project's PI approves.
    """
    from accounts.models import CustomUser

    if linked_project is None or linked_project.pi_id == employee.id:
        director = CustomUser.objects.filter(role='DIRECTOR', is_archived=False).first()
        return director
    return linked_project.pi


# ── PORTAL HOME ──────────────────────────────────────────────────────

@login_required
def portal_home(request):
    profile = getattr(request.user, 'employee_profile', None)
    profile_completed = profile.profile_completed if profile else False

    led_or_coordinated_studies = Study.objects.filter(
        Q(pi=request.user) | Q(coordinator=request.user)
    ).distinct()
    pending_approvals = StudyBondApplication.objects.filter(
        approver=request.user, status=StudyBondApplication.Status.PENDING_APPROVAL
    )
    my_applications = StudyBondApplication.objects.filter(employee=request.user)[:5]

    context = {
        'profile_completed': profile_completed,
        'led_or_coordinated_studies': led_or_coordinated_studies,
        'pending_approvals': pending_approvals,
        'my_applications': my_applications,
    }
    return render(request, 'employee_services/portal_home.html', context)


# ── STUDY DIRECTORY (read-only for everyone) ─────────────────────────

@login_required
def study_directory(request):
    studies = Study.objects.select_related('pi', 'coordinator').all()
    return render(request, 'employee_services/study_directory.html', {'studies': studies})


# ── STUDY BOND: LIST / DETAIL ─────────────────────────────────────────

@login_required
def study_bond_list(request):
    applications = StudyBondApplication.objects.filter(employee=request.user)
    return render(request, 'employee_services/study_bond_list.html', {'applications': applications})


@login_required
@owner_or_admin_hr_required
def study_bond_detail(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)
    can_verify_grade = (
        application.is_continuation()
        and application.previous_application
        and application.previous_application.grade_status == StudyBondApplication.GradeStatus.PENDING
        and request.user.role in ('HR', 'ADMIN')
    )
    context = {
        'application': application,
        'is_approver': request.user == application.approver,
        'can_verify_grade': can_verify_grade,
        'max_allowed': application.max_allowed_bup_amount(),
    }
    return render(request, 'employee_services/study_bond_detail.html', context)


# ── FRESH APPLICATION ─────────────────────────────────────────────────

@login_required
def study_bond_apply(request):
    if request.method == 'POST':
        form = StudyBondApplicationForm(request.POST)
        attachments_form = StudyBondFreshAttachmentsForm(request.POST, request.FILES)
        if form.is_valid() and attachments_form.is_valid():
            application = form.save(commit=False)
            application.application_type = StudyBondApplication.ApplicationType.FRESH
            application.employee = request.user
            application.submitted_at = timezone.now()
            application.approver = determine_approver(request.user, application.linked_project)
            application.status = StudyBondApplication.Status.PENDING_HR_REVIEW
            application.save()
            attachments_form.save(application)

            log_action(request, 'STUDY_BOND_SUBMITTED',
                       description=f'{request.user} submitted a fresh Study Bond application ({application.program_title}).')
            notify('study_bond_submitted', recipient=application.approver, context={'application': application})

            messages.success(request, 'Your Study Bond application has been submitted.')
            return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = StudyBondApplicationForm()
        attachments_form = StudyBondFreshAttachmentsForm()

    return render(request, 'employee_services/study_bond_apply.html', {
        'form': form, 'attachments_form': attachments_form,
    })


# ── CONTINUATION ───────────────────────────────────────────────────────

@login_required
def study_bond_apply_continuation(request):
    if request.method == 'POST':
        form = ContinuationRequestForm(request.POST, employee=request.user)
        attachments_form = ContinuationAttachmentsForm(request.POST, request.FILES)
        if form.is_valid() and attachments_form.is_valid():
            previous = form.cleaned_data['previous_application']

            application = StudyBondApplication.objects.create(
                application_type=StudyBondApplication.ApplicationType.CONTINUATION,
                employee=request.user,
                previous_application=previous,
                # Inherited, not re-entered:
                linked_project=previous.linked_project,
                approver=previous.approver,
                program_title=previous.program_title,
                institution=previous.institution,
                period_start=previous.period_start,
                period_end=previous.period_end,
                total_cost=previous.total_cost,
                policy_acknowledged=form.cleaned_data['policy_acknowledged'],
                status=StudyBondApplication.Status.PENDING_HR_REVIEW,
            )
            attachments_form.save(application)

            log_action(request, 'STUDY_BOND_CONTINUATION_SUBMITTED',
                       description=f'{request.user} submitted a Study Bond continuation of application #{previous.pk}.')
            notify('study_bond_continuation_submitted', recipient=application.approver, context={'application': application})

            messages.success(request, 'Your continuation request has been submitted.')
            return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = ContinuationRequestForm(employee=request.user)
        attachments_form = ContinuationAttachmentsForm()

    return render(request, 'employee_services/study_bond_continuation_apply.html', {
        'form': form, 'attachments_form': attachments_form,
    })


# ── GRADE VERIFICATION (gates continuation; HR only; acts on the PREVIOUS application) ─

@login_required
def study_bond_verify_grade(request, pk):
    """
    pk here is the CONTINUATION application. This view verifies the grade
    on its previous_application — that's the record grade_status actually
    lives on and always has, fresh or not.
    """
    continuation = get_object_or_404(StudyBondApplication, pk=pk)
    if request.user.role not in ('HR', 'ADMIN'):
        return redirect('accounts:access_denied')
    if not continuation.is_continuation() or continuation.previous_application is None:
        return redirect('employee_services:study_bond_detail', pk=pk)

    previous = continuation.previous_application

    if request.method == 'POST':
        form = GradeVerificationForm(request.POST)
        if form.is_valid():
            previous.grade_status = form.cleaned_data['grade_status']
            previous.grade_notes = form.cleaned_data['grade_notes']
            previous.grade_verified_by = request.user
            previous.grade_verified_at = timezone.now()
            previous.save()

            log_action(request, 'STUDY_BOND_GRADE_VERIFIED',
                       description=f'{request.user} recorded grade "{previous.grade_status}" for application #{previous.pk}.')

            if previous.grade_status == StudyBondApplication.GradeStatus.FAILED:
                continuation.status = StudyBondApplication.Status.DECLINED
                continuation.hr_notes = f"Continuation declined — prior grade verification failed. {form.cleaned_data['grade_notes']}"
                continuation.save()
                log_action(request, 'STUDY_BOND_DECLINED',
                           description=f'Continuation #{continuation.pk} declined — prior grade failed.')
                notify('study_bond_continuation_declined', recipient=continuation.employee, context={'application': continuation})
                messages.warning(request, 'Continuation declined — the prior grade verification did not pass.')
            else:
                messages.success(request, 'Grade verified as passed — continuation proceeds to cost review.')

            return redirect('employee_services:study_bond_detail', pk=continuation.pk)
    else:
        form = GradeVerificationForm()

    return render(request, 'employee_services/study_bond_verify_grade.html', {
        'form': form, 'continuation': continuation, 'previous': previous,
    })


# ── HR REVIEW ────────────────────────────────────────────────────────

@login_required
@hr_review_required
def study_bond_hr_review(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)

    # Continuation gate: can't proceed to cost review until the prior
    # grade has been verified as PASSED.
    if application.is_continuation() and application.previous_application.grade_status == StudyBondApplication.GradeStatus.PENDING:
        return redirect('employee_services:study_bond_verify_grade', pk=pk)

    if request.method == 'POST':
        form = HRReviewForm(request.POST, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            application.hr_reviewed_by = request.user
            application.hr_reviewed_at = timezone.now()
            application.status = StudyBondApplication.Status.PENDING_APPROVAL
            application.save()

            log_action(request, 'STUDY_BOND_HR_REVIEWED',
                       description=f'{request.user} completed HR review on application #{application.pk}.')
            notify('study_bond_pending_approval', recipient=application.approver, context={'application': application})

            messages.success(request, 'HR review complete — sent to approver.')
            return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = HRReviewForm(instance=application)

    return render(request, 'employee_services/study_bond_hr_review.html', {
        'form': form, 'application': application,
    })


# ── APPROVER REVIEW ────────────────────────────────────────────────────

@login_required
@approver_required
def study_bond_approver_review(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)

    if request.method == 'POST':
        form = ApproverReviewForm(request.POST, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            decision = form.cleaned_data['decision']
            application.status = decision
            application.decision_date = timezone.now()
            application.save()

            if decision == 'APPROVED':
                application.status = StudyBondApplication.Status.PENDING_PAYMENT
                application.save()
                log_action(request, 'STUDY_BOND_APPROVED',
                           description=f'{request.user} approved application #{application.pk}.')
                notify('study_bond_approved', recipient=application.employee, context={'application': application})
                messages.success(request, 'Application approved — sent to Finance.')
            else:
                log_action(request, 'STUDY_BOND_DECLINED',
                           description=f'{request.user} declined application #{application.pk}.')
                notify('study_bond_declined', recipient=application.employee, context={'application': application})
                messages.warning(request, 'Application declined.')

            return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = ApproverReviewForm(instance=application)

    return render(request, 'employee_services/study_bond_approver_review.html', {
        'form': form, 'application': application,
    })


# ── FINANCE PROCESSING ──────────────────────────────────────────────────

@login_required
@finance_required
def study_bond_finance_process(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)

    if request.method == 'POST':
        form = FinanceProcessForm(request.POST, request.FILES, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            application.finance_processed_by = request.user
            application.finance_processed_at = timezone.now()
            application.status = StudyBondApplication.Status.COMPLETED
            application.save()

            log_action(request, 'STUDY_BOND_PAID',
                       description=f'{request.user} processed payment for application #{application.pk}.')
            notify('study_bond_paid', recipient=application.employee, context={'application': application})
            notify('study_bond_paid', recipient=application.hr_reviewed_by, context={'application': application})

            messages.success(request, 'Payment processed. Documents sent to employee and HR.')
            return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = FinanceProcessForm(instance=application)

    return render(request, 'employee_services/study_bond_finance_process.html', {
        'form': form, 'application': application,
    })


# ── PDF DOWNLOAD ─────────────────────────────────────────────────────────

@login_required
@owner_or_admin_hr_required
def study_bond_pdf_download(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)
    from .pdf_utils import generate_study_bond_pdf
    pdf_buffer = generate_study_bond_pdf(application)

    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"Study_Bond_{application.employee.get_full_name().replace(' ', '_')}_{application.pk}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

