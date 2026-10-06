import mimetypes
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from accounts.decorators import role_required
from core.notifications import notify
from core.utils import get_client_ip, log_action
from research.models import Study

from .approval_links import find_active_token, issue_link, latest_token, link_url, revoke_links, token_is_usable
from .decorators import (
    approver_required, finance_required, hr_review_required, owner_or_admin_hr_required,
)
from .forms import (
    ApproverReviewForm, ChangeApproverForm, ContinuationAttachmentsForm, ContinuationRequestForm,
    EditAttachmentsForm, FinanceProcessForm, GradeVerificationForm, HRReviewForm, ReturnForm,
    StudyBondApplicationForm, StudyBondEditForm, StudyBondFreshAttachmentsForm, WithdrawForm,
)
from .models import ApprovalToken, StudyBondApplication, StudyBondAttachment, StudyBondReturn
from .routing import apply_approver_choice, approver_link_profile, determine_approver, person_name

S = StudyBondApplication.Status


def _denied(reason):
    from urllib.parse import urlencode
    return redirect(f"/accounts/access-denied/?{urlencode({'reason': reason})}")


# ── PORTAL HOME ─────────────────────────────────────────────────────

@login_required
def portal_home(request):
    profile = getattr(request.user, 'employee_profile', None)
    profile_completed = profile.profile_completed if profile else False

    led_or_coordinated_studies = Study.objects.filter(
        Q(pi=request.user) | Q(coordinator=request.user)
    ).distinct()
    pending_approvals = StudyBondApplication.objects.filter(
        approver=request.user, status=S.PENDING_APPROVAL
    )
    my_applications = StudyBondApplication.objects.filter(employee=request.user)[:5]

    context = {
        'profile_completed': profile_completed,
        'led_or_coordinated_studies': led_or_coordinated_studies,
        'pending_approvals': pending_approvals,
        'my_applications': my_applications,
    }
    return render(request, 'employee_services/portal_home.html', context)


# ── STUDY DIRECTORY (read-only for everyone) ────────────────────────

@login_required
def study_directory(request):
    studies = Study.objects.select_related('pi', 'coordinator').all()
    return render(request, 'employee_services/study_directory.html', {'studies': studies})


# ── STUDY BOND: LIST / DETAIL ───────────────────────────────────────

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
        'is_owner': request.user == application.employee,
        'is_approver': request.user == application.approver,
        'can_verify_grade': can_verify_grade,
        'max_allowed': application.max_allowed_bup_amount(),
    }
    return render(request, 'employee_services/study_bond_detail.html', context)


# ── FRESH APPLICATION ───────────────────────────────────────────────

@login_required
def study_bond_apply(request):
    if request.method == 'POST':
        form = StudyBondApplicationForm(request.POST, employee=request.user)
        attachments_form = StudyBondFreshAttachmentsForm(request.POST, request.FILES)
        if form.is_valid() and attachments_form.is_valid():
            application = form.save(commit=False)
            application.application_type = StudyBondApplication.ApplicationType.FRESH
            application.employee = request.user
            application.submitted_at = timezone.now()
            application.approver = determine_approver(request.user, application.linked_project)
            application.status = S.PENDING_HR_REVIEW
            if application.approver is None:
                messages.error(request, 'No approver could be found for this application. Please contact the system administrator.')
            else:
                application.save()
                attachments_form.save(application)

                log_action(request, 'STUDY_BOND_SUBMITTED',
                           description=f'{request.user} submitted a fresh Study Bond application ({application.program_title}).')
                notify('study_bond_submitted', recipient=application.approver, context={'application': application})

                messages.success(request, 'Your Study Bond application has been submitted.')
                return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = StudyBondApplicationForm(employee=request.user)
        attachments_form = StudyBondFreshAttachmentsForm()

    return render(request, 'employee_services/study_bond_apply.html', {
        'form': form, 'attachments_form': attachments_form,
    })


# ── CONTINUATION ────────────────────────────────────────────────────

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
                status=S.PENDING_HR_REVIEW,
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


# ── EDIT AND RESUBMIT (after HR returned it) ────────────────────────

@login_required
def study_bond_edit(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)
    if request.user != application.employee:
        return _denied("Only the employee who submitted an application can edit it.")
    if not application.can_edit:
        messages.info(request, 'This application is not waiting for changes.')
        return redirect('employee_services:study_bond_detail', pk=pk)

    is_continuation = application.is_continuation()

    if request.method == 'POST':
        form = None if is_continuation else StudyBondEditForm(request.POST, instance=application, employee=request.user)
        attachments_form = EditAttachmentsForm(request.POST, request.FILES, application=application)
        if (form is None or form.is_valid()) and attachments_form.is_valid():
            problem = None
            with transaction.atomic():
                if form is not None:
                    application = form.save(commit=False)
                    # Only re-route if the employee changed the study. Otherwise keep whoever
                    # is the approver now, which may be a choice HR made on purpose.
                    if 'linked_project' in form.changed_data:
                        new_approver = determine_approver(request.user, application.linked_project)
                        if new_approver is None:
                            problem = 'No approver could be found for this study. Please contact the system administrator.'
                        else:
                            application.approver = new_approver
                if problem is None:
                    attachments_form.save(application)
                    application.status = S.PENDING_HR_REVIEW
                    application.round_number += 1
                    application.save()
                    application.returns.filter(resubmitted_at__isnull=True).update(resubmitted_at=timezone.now())
            if problem:
                messages.error(request, problem)
            else:
                log_action(request, 'STUDY_BOND_RESUBMITTED',
                           description=f'{request.user} resubmitted application #{application.pk} (round {application.round_number}).')
                notify('study_bond_resubmitted', recipient=application.approver, context={'application': application})
                messages.success(request, 'Your changes have been sent back to HR for review.')
                return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = None if is_continuation else StudyBondEditForm(instance=application, employee=request.user)
        attachments_form = EditAttachmentsForm(application=application)

    return render(request, 'employee_services/study_bond_edit.html', {
        'application': application, 'form': form, 'attachments_form': attachments_form,
        'latest_return': application.latest_return,
    })


# ── WITHDRAW ────────────────────────────────────────────────────────

@login_required
def study_bond_withdraw(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)
    if request.user != application.employee:
        return _denied("Only the employee who submitted an application can withdraw it.")
    if not application.can_withdraw:
        messages.info(request, 'This application can no longer be withdrawn. Please speak to HR.')
        return redirect('employee_services:study_bond_detail', pk=pk)

    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            was_with_approver = application.status == S.PENDING_APPROVAL
            application.status = S.WITHDRAWN
            application.withdrawn_at = timezone.now()
            application.withdrawn_reason = form.cleaned_data['reason']
            application.save()
            revoke_links(application)

            log_action(request, 'STUDY_BOND_WITHDRAWN',
                       description=f'{request.user} withdrew application #{application.pk}.')
            notify('study_bond_withdrawn', recipient=application.approver,
                   context={'application': application, 'notify_approver': was_with_approver})

            messages.success(request, 'Your application has been withdrawn.')
            return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = WithdrawForm()

    return render(request, 'employee_services/study_bond_withdraw.html', {
        'form': form, 'application': application,
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
                continuation.status = S.DECLINED
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


# ── HR REVIEW ───────────────────────────────────────────────────────

@login_required
@hr_review_required
def study_bond_hr_review(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)

    # Continuation gate: can't proceed to cost review until the prior
    # grade has been verified as PASSED.
    if application.is_continuation() and application.previous_application.grade_status == StudyBondApplication.GradeStatus.PENDING:
        return redirect('employee_services:study_bond_verify_grade', pk=pk)

    action = request.POST.get('action', 'send') if request.method == 'POST' else None
    form = HRReviewForm(instance=application)
    return_form = ReturnForm()
    change_form = ChangeApproverForm(application=application)
    pi_profile = approver_link_profile(application.approver)
    pi_problem = None

    if request.method == 'POST' and action == 'change_approver':
        change_form = ChangeApproverForm(request.POST, application=application)
        if change_form.is_valid():
            before = person_name(application.approver)
            changed = apply_approver_choice(application, change_form.cleaned_data['approver'])
            if not changed:
                messages.info(request, 'The approver was not changed.')
            elif application.approver is None:
                messages.error(request, 'There is no Director account to send this to.')
            else:
                application.save(update_fields=['linked_project', 'approver'])
                log_action(request, 'STUDY_BOND_APPROVER_CHANGED',
                           description=f'{request.user} changed the approver on application #{application.pk} from {before} to {person_name(application.approver)}.')
                messages.success(request, f'This application will now go to {person_name(application.approver)}.')
            return redirect('employee_services:study_bond_hr_review', pk=pk)

    elif request.method == 'POST' and action == 'return':
        return_form = ReturnForm(request.POST)
        if return_form.is_valid():
            reason = return_form.cleaned_data['reason']
            with transaction.atomic():
                StudyBondReturn.objects.create(application=application, returned_by=request.user, reason=reason)
                application.status = S.RETURNED
                application.save(update_fields=['status'])
                revoke_links(application)
            log_action(request, 'STUDY_BOND_RETURNED',
                       description=f'{request.user} returned application #{application.pk} to {application.employee} for changes.')
            notify('study_bond_returned', recipient=application.employee,
                   context={'application': application, 'reason': reason})
            messages.success(request, 'Returned to the employee. They have been emailed your note.')
            return redirect('employee_services:study_bond_hr_queue')

    elif request.method == 'POST':
        form = HRReviewForm(request.POST, instance=application)
        confirmed = bool(request.POST.get('confirm_pi_email'))
        valid = form.is_valid()
        if pi_profile is not None:
            if not pi_profile.approval_email:
                pi_problem = 'This PI has no approval email address. Ask an administrator to add one before this can be sent.'
            elif not pi_profile.email_checked and not confirmed:
                pi_problem = 'Please confirm that the approval email address shown is correct before sending.'
        if valid and pi_problem is None:
            application = form.save(commit=False)
            application.hr_reviewed_by = request.user
            application.hr_reviewed_at = timezone.now()
            application.status = S.PENDING_APPROVAL
            application.save()

            log_action(request, 'STUDY_BOND_HR_REVIEWED',
                       description=f'{request.user} completed HR review on application #{application.pk}.')

            context = {'application': application}
            if pi_profile is not None:
                if confirmed and not pi_profile.email_checked:
                    pi_profile.mark_email_checked(request.user)
                raw, token = issue_link(application, pi_profile)
                context.update(approval_link=link_url(raw), link_expires=token.expires_at)
                log_action(request, 'STUDY_BOND_LINK_SENT',
                           description=f'Approval link for application #{application.pk} emailed to {pi_profile.approval_email}.')

            logs = notify('study_bond_pending_approval', recipient=application.approver, context=context)

            if pi_profile is not None:
                problem = next((entry for entry in (logs or []) if entry is not None and entry.status != 'SENT'), None)
                if problem is not None:
                    messages.warning(request, f'HR review complete, but the approval link could not be emailed '
                                              f'({problem.error or problem.get_status_display()}). '
                                              f'Use Resend on the Waiting page once that is fixed.')
                else:
                    messages.success(request, f'HR review complete. An approval link has been emailed to {pi_profile.display_name}.')
            else:
                messages.success(request, 'HR review complete — sent to approver.')
            return redirect('employee_services:study_bond_detail', pk=application.pk)

    return render(request, 'employee_services/study_bond_hr_review.html', {
        'form': form, 'application': application,
        'return_form': return_form, 'change_form': change_form,
        'pi_profile': pi_profile, 'pi_problem': pi_problem,
    })


# ── APPROVER DECISION (shared by the signed-in page and the emailed link) ──

def _record_decision(request, form, via_link=False, link=None):
    """
    Apply an approver's decision exactly once. `form` is a valid ApproverReviewForm.
    For a link decision there is no signed-in user, so the audit entry names the
    approver and says it was done by the emailed link.
    """
    application = form.save(commit=False)
    decision = form.cleaned_data['decision']
    now = timezone.now()
    application.decision_date = now
    if decision == 'APPROVED':
        application.status = S.PENDING_PAYMENT
        application.approved_by_link = via_link
    else:
        application.status = S.DECLINED
    application.save()

    if link is not None:
        link.used_at = now
        link.used_ip = get_client_ip(request)
        link.save(update_fields=['used_at', 'used_ip'])

    who = person_name(application.approver) if via_link else str(request.user)
    how = ' using the emailed approval link' if via_link else ''
    target = application.approver if via_link else None
    if decision == 'APPROVED':
        log_action(request, 'STUDY_BOND_APPROVED', target_user=target,
                   description=f'{who} approved application #{application.pk}{how}.')
        notify('study_bond_approved', recipient=application.employee, context={'application': application})
    else:
        log_action(request, 'STUDY_BOND_DECLINED', target_user=target,
                   description=f'{who} declined application #{application.pk}{how}.')
        notify('study_bond_declined', recipient=application.employee, context={'application': application})
    return decision


# ── APPROVER REVIEW (signed in) ─────────────────────────────────────

@login_required
@approver_required
def study_bond_approver_review(request, pk):
    application = get_object_or_404(StudyBondApplication, pk=pk)

    if request.method == 'POST':
        form = ApproverReviewForm(request.POST, instance=application)
        if form.is_valid():
            decision = _record_decision(request, form)
            if decision == 'APPROVED':
                messages.success(request, 'Application approved — sent to Finance.')
            else:
                messages.warning(request, 'Application declined.')
            return redirect('employee_services:study_bond_detail', pk=application.pk)
    else:
        form = ApproverReviewForm(instance=application)

    return render(request, 'employee_services/study_bond_approver_review.html', {
        'form': form, 'application': application,
    })


# ── FINANCE PROCESSING ──────────────────────────────────────────────

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
            application.status = S.COMPLETED
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


# ── PDF DOWNLOAD ────────────────────────────────────────────────────

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


# ── QUEUES ──────────────────────────────────────────────────────────

@login_required
@role_required('HR', 'ADMIN')
def study_bond_hr_queue(request):
    """
    HR's work queue. Pending: waiting on HR right now. Completed: HR has
    already reviewed it (regardless of what's happened downstream since —
    approved, declined, paid — this is HR's own history, not the
    application's current status).
    """
    pending = StudyBondApplication.objects.filter(
        status=S.PENDING_HR_REVIEW
    ).select_related('employee')
    completed = StudyBondApplication.objects.filter(
        hr_reviewed_by__isnull=False
    ).select_related('employee').order_by('-hr_reviewed_at')
    return render(request, 'employee_services/study_bond_hr_queue.html', {
        'pending': pending,
        'completed': completed,
    })


@login_required
def study_bond_approver_queue(request):
    """
    An approver's own queue — filtered to THEM specifically, both halves.
    Pending: awaiting their decision. Completed: they've already decided
    (approved or declined), most recent first.
    """
    pending = StudyBondApplication.objects.filter(
        approver=request.user,
        status=S.PENDING_APPROVAL,
    ).select_related('employee')
    completed = StudyBondApplication.objects.filter(
        approver=request.user,
        decision_date__isnull=False,
    ).select_related('employee').order_by('-decision_date')
    return render(request, 'employee_services/study_bond_approver_queue.html', {
        'pending': pending,
        'completed': completed,
    })


@login_required
@role_required('FINANCE', 'ADMIN')
def study_bond_finance_queue(request):
    """
    Finance's work queue. Pending: approved and waiting for payment.
    Completed: Finance has already processed it, regardless of who
    processed it — this is a shared departmental history.
    """
    pending = StudyBondApplication.objects.filter(
        status=S.PENDING_PAYMENT
    ).select_related('employee')
    completed = StudyBondApplication.objects.filter(
        finance_processed_by__isnull=False
    ).select_related('employee').order_by('-finance_processed_at')
    return render(request, 'employee_services/study_bond_finance_queue.html', {
        'pending': pending,
        'completed': completed,
    })


# ── WAITING ON OTHERS (HR): PIs who have a link, and employees who must fix something ──

@login_required
@role_required('HR', 'ADMIN')
def study_bond_waiting(request):
    now = timezone.now()

    on_pi = []
    for application in StudyBondApplication.objects.filter(status=S.PENDING_APPROVAL).select_related('employee', 'approver'):
        profile = approver_link_profile(application.approver)
        if profile is None:
            continue
        token = latest_token(application)
        since = application.hr_reviewed_at or application.submitted_at
        on_pi.append({
            'application': application, 'profile': profile, 'token': token,
            'days': (now - since).days if since else 0,
            'link_alive': token is not None and token_is_usable(token, now),
        })
    on_pi.sort(key=lambda row: -row['days'])

    returned = []
    for application in StudyBondApplication.objects.filter(status=S.RETURNED).select_related('employee'):
        ret = application.latest_return
        returned.append({
            'application': application, 'ret': ret,
            'days': (now - ret.returned_at).days if ret else 0,
        })
    returned.sort(key=lambda row: -row['days'])

    return render(request, 'employee_services/study_bond_waiting.html', {
        'on_pi': on_pi, 'returned': returned,
    })


@login_required
@role_required('HR', 'ADMIN')
def study_bond_resend_link(request, pk):
    if request.method != 'POST':
        return redirect('employee_services:study_bond_waiting')
    application = get_object_or_404(StudyBondApplication, pk=pk)
    profile = approver_link_profile(application.approver)

    if application.status != S.PENDING_APPROVAL or profile is None:
        messages.error(request, 'This application is not waiting on an approval link.')
    elif not profile.email_checked:
        messages.error(request, 'The PI\'s approval email has not been checked yet. Confirm it on the HR review screen or ask an administrator.')
    else:
        raw, token = issue_link(application, profile)
        logs = notify('study_bond_pending_approval', recipient=application.approver, context={
            'application': application, 'approval_link': link_url(raw),
            'link_expires': token.expires_at, 'resend': True,
        })
        log_action(request, 'STUDY_BOND_LINK_SENT',
                   description=f'{request.user} resent the approval link for application #{application.pk} to {profile.approval_email}.')
        problem = next((entry for entry in (logs or []) if entry is not None and entry.status != 'SENT'), None)
        if problem is not None:
            messages.warning(request, f'A new link was made, but it could not be emailed ({problem.error or problem.get_status_display()}).')
        else:
            messages.success(request, f'A new approval link has been emailed to {profile.display_name}. The old one no longer works.')
    return redirect('employee_services:study_bond_waiting')


# ── PUBLIC: THE APPROVER'S EMAILED LINK (no sign-in) ────────────────
# Everything below is reachable without signing in, so it trusts nothing but the link's secret,
# says nothing about WHY a link is invalid, and never caches a page.

def _public(request, template, context, status=200):
    response = render(request, template, context, status=status)
    # 'same-origin' keeps the link's secret from ever being sent to another site. It must NOT be
    # 'no-referrer': browsers answer that by sending "Origin: null" on form posts, and Django's
    # CSRF check then refuses the Approve and Decline buttons.
    response['Referrer-Policy'] = 'same-origin'
    return response


_INLINE_SAFE = ('application/pdf', 'image/png', 'image/jpeg', 'image/gif')


@never_cache
def link_review(request, token):
    link = find_active_token(token)
    if link is None:
        return _public(request, 'employee_services/public/link_invalid.html', {}, status=404)

    application = link.application
    context = {
        'application': application, 'token': token, 'link': link,
        'attachments': application.current_attachments,
        'approver_name': person_name(application.approver),
        'max_allowed': application.max_allowed_bup_amount(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        form = ApproverReviewForm(request.POST, instance=application)

        if action == 'edit':
            context['form'] = form
            return _public(request, 'employee_services/public/link_review.html', context)

        if action == 'confirm':
            # Re-check under a lock, so a double click can never record two decisions.
            with transaction.atomic():
                locked = ApprovalToken.objects.select_for_update().get(pk=link.pk)
                fresh = StudyBondApplication.objects.select_for_update().get(pk=locked.application_id)
                locked.application = fresh
                if not token_is_usable(locked):
                    return _public(request, 'employee_services/public/link_invalid.html', {}, status=404)
                fresh_form = ApproverReviewForm(request.POST, instance=fresh)
                if fresh_form.is_valid():
                    _record_decision(request, fresh_form, via_link=True, link=locked)
                    return redirect('employee_services:link_thanks')
            context['form'] = fresh_form
            return _public(request, 'employee_services/public/link_review.html', context)

        if form.is_valid():
            # First press of Approve or Decline: show a summary and ask for one more confirmation.
            checklist = []
            for name in ('program_relevant', 'accredited_institution', 'good_standing_6_months',
                         'tuition_cap_balance_ok', 'supervisor_notified'):
                value = form.cleaned_data.get(name)
                checklist.append((form.fields[name].label or name,
                                  'Yes' if value is True else ('No' if value is False else 'Not answered')))
            context.update({
                'form': form,
                'decision': form.cleaned_data['decision'],
                'checklist': checklist,
                'posted': [(name, request.POST.get(name, '')) for name in list(form.fields) if name in request.POST],
            })
            return _public(request, 'employee_services/public/link_confirm.html', context)

        context['form'] = form
        return _public(request, 'employee_services/public/link_review.html', context)

    context['form'] = ApproverReviewForm(instance=application)
    return _public(request, 'employee_services/public/link_review.html', context)


@never_cache
def link_attachment(request, token, att_id):
    link = find_active_token(token)
    if link is None:
        raise Http404
    attachment = get_object_or_404(
        StudyBondAttachment, pk=att_id, application=link.application, superseded_at__isnull=True,
    )
    name = os.path.basename(attachment.file.name)
    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    response = FileResponse(
        attachment.file.open('rb'),
        as_attachment=content_type not in _INLINE_SAFE,   # only PDFs and images open in the browser
        filename=name,
        content_type=content_type,
    )
    response['X-Content-Type-Options'] = 'nosniff'
    response['Referrer-Policy'] = 'no-referrer'
    return response


@never_cache
def link_thanks(request):
    return _public(request, 'employee_services/public/link_thanks.html', {})