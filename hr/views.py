import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from accounts.decorators import role_required
from accounts.models import CustomUser
from director.models import DirectorProfile
from .models import HRForm, ConfirmationLetter, ExtracurricularActivity, UserRequest, HRProfile,StudyBondRequest,_snapshot_signature


# ── EMPLOYEE DIRECTORY ────────────────────────────────────────────

@login_required
@role_required('ADMIN', 'HR', 'DIRECTOR')
def employee_directory(request):
    search = request.GET.get('search', '').strip()
    department = request.GET.get('department', '').strip()
    role_filter = request.GET.get('role', '').strip()

    employees = CustomUser.objects.filter(
        is_archived=False,
        is_active=True,
    ).exclude(role=None).order_by('first_name', 'last_name')

    if search:
        employees = employees.filter(
            first_name__icontains=search
        ) | employees.filter(
            last_name__icontains=search
        ) | employees.filter(
            email__icontains=search
        )

    if department:
        employees = employees.filter(department__icontains=department)

    if role_filter:
        employees = employees.filter(role=role_filter)

    role_choices = CustomUser.ROLE_CHOICES
    departments = CustomUser.objects.filter(
        is_archived=False
    ).exclude(department=None).exclude(
        department=''
    ).values_list('department', flat=True).distinct()

    context = {
        'employees': employees,
        'search': search,
        'department': department,
        'role_filter': role_filter,
        'role_choices': role_choices,
        'departments': departments,
        'total_count': employees.count(),
    }
    return render(request, 'hr/employee_directory.html', context)


# ── CONFIRMATION LETTERS ─────────────────────────────────────────

@login_required
@role_required('HR', 'ADMIN')
def confirmation_letter_list(request):
    letters = ConfirmationLetter.objects.select_related('employee', 'created_by').all()
    context = {'letters': letters}
    return render(request, 'hr/confirmation_letter_list.html', context)


@login_required
@role_required('HR', 'ADMIN')
def confirmation_letter_create(request):
    employees = CustomUser.objects.filter(
        is_archived=False,
        is_active=True
    ).order_by('first_name', 'last_name')

    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        salutation = request.POST.get('salutation')
        employee_id_number = request.POST.get('employee_id_number', '')
        job_title = request.POST.get('job_title')
        annual_salary = request.POST.get('annual_salary', '')
        plot_number = request.POST.get('plot_number', '')
        ward = request.POST.get('ward', '')
        po_box = request.POST.get('po_box', '')
        postal_city = request.POST.get('postal_city', 'Gaborone')
        purpose = request.POST.get('purpose', '')

        if not all([employee_id, salutation, job_title]):
            messages.error(request, 'Please fill in all required fields.')
        else:
            employee = get_object_or_404(CustomUser, id=employee_id)
            letter = ConfirmationLetter.objects.create(
                employee=employee,
                salutation=salutation,
                employee_id_number=employee_id_number,
                job_title=job_title,
                annual_salary=annual_salary if annual_salary else None,
                plot_number=plot_number,
                ward=ward,
                po_box=po_box,
                postal_city=postal_city,
                purpose=purpose,
                created_by=request.user,
            )
            messages.success(request, f'Confirmation letter created for {employee.get_full_name()}.')
            return redirect('hr:confirmation_letter_download', pk=letter.pk)

    context = {
        'employees': employees,
        'salutation_choices': ConfirmationLetter.SALUTATION_CHOICES,
    }
    return render(request, 'hr/confirmation_letter_create.html', context)


@login_required
def confirmation_letter_download(request, pk):
    letter = get_object_or_404(ConfirmationLetter, pk=pk)
    user = request.user
    if user.role not in ('HR', 'ADMIN', 'DIRECTOR') and user != letter.employee:
        return redirect('accounts:access_denied')

    try:
        hr_profile = HRProfile.objects.get(is_active=True)
    except HRProfile.DoesNotExist:
        messages.error(request, 'No active HR profile found. Please contact IT Admin.')
        return redirect('hr:confirmation_letter_list')

    from .pdf_utils import generate_confirmation_letter_pdf
    pdf_buffer = generate_confirmation_letter_pdf(letter, hr_profile, request)

    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"Confirmation_Letter_{letter.employee.get_full_name().replace(' ', '_')}_{letter.date_issued}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── HR FORMS ──────────────────────────────────────────────────────

@login_required
@role_required('HR', 'ADMIN')
def hr_form_list(request):
    forms = HRForm.objects.all().order_by('-created_at')
    context = {'forms': forms}
    return render(request, 'hr/hr_form_list.html', context)


@login_required
@role_required('HR', 'ADMIN')
def hr_form_upload(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        file = request.FILES.get('file')

        if not title or not file:
            messages.error(request, 'Title and file are required.')
        else:
            HRForm.objects.create(
                title=title,
                description=description,
                file=file,
                uploaded_by=request.user,
            )
            messages.success(request, f'Form "{title}" uploaded successfully.')
            return redirect('hr:hr_form_list')

    return render(request, 'hr/hr_form_upload.html')


@login_required
@role_required('HR', 'ADMIN')
def hr_form_toggle(request, pk):
    form = get_object_or_404(HRForm, pk=pk)
    form.is_active = not form.is_active
    form.save()
    status = 'activated' if form.is_active else 'deactivated'
    messages.success(request, f'Form "{form.title}" {status}.')
    return redirect('hr:hr_form_list')


@login_required
def hr_form_download(request, pk):
    import mimetypes
    from django.conf import settings
    form = get_object_or_404(HRForm, pk=pk, is_active=True)
    file_path = os.path.join(settings.MEDIA_ROOT, str(form.file))
    if not os.path.exists(file_path):
        messages.error(request, 'File not found.')
        return redirect('hr:hr_form_list')
    mime_type, _ = mimetypes.guess_type(file_path)
    with open(file_path, 'rb') as f:
        response = HttpResponse(
            f.read(),
            content_type=mime_type or 'application/octet-stream'
        )
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
    return response


# ── EXTRACURRICULAR ACTIVITIES ────────────────────────────────────

@login_required
@role_required('HR', 'ADMIN', 'DIRECTOR')
def activity_list(request):
    activities = ExtracurricularActivity.objects.select_related(
        'submitted_by', 'actioned_by'
    ).all()
    context = {'activities': activities}
    return render(request, 'hr/activity_list.html', context)


@login_required
@role_required('HR', 'ADMIN')
def activity_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        proposed_date = request.POST.get('proposed_date')
        estimated_cost = request.POST.get('estimated_cost', '')

        if not all([title, description, proposed_date]):
            messages.error(request, 'Please fill in all required fields.')
        else:
            ExtracurricularActivity.objects.create(
                title=title,
                description=description,
                proposed_date=proposed_date,
                estimated_cost=estimated_cost if estimated_cost else None,
                submitted_by=request.user,
                status='SUBMITTED',
            )
            messages.success(request, f'Activity "{title}" submitted for Director approval.')
            return redirect('hr:activity_list')

    return render(request, 'hr/activity_create.html')


@login_required
@role_required('DIRECTOR', 'ADMIN')
def activity_action(request, pk):
    activity = get_object_or_404(ExtracurricularActivity, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('director_comment', '').strip()

        if action == 'approve':
            activity.status = 'APPROVED'
        elif action == 'decline':
            activity.status = 'DECLINED'

        activity.director_comment = comment
        activity.actioned_by = request.user
        activity.save()

        messages.success(request, f'Activity "{activity.title}" {activity.status.lower()}.')
        return redirect('hr:activity_list')

    context = {'activity': activity}
    return render(request, 'hr/activity_action.html', context)


# ── USER REQUESTS ─────────────────────────────────────────────────

@login_required
@role_required('HR', 'ADMIN')
def user_request_list(request):
    requests_qs = UserRequest.objects.select_related('submitted_by').all()
    context = {'requests': requests_qs}
    return render(request, 'hr/user_request_list.html', context)


@login_required
@role_required('HR', 'ADMIN')
def user_request_create(request):
    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        employee_name = request.POST.get('employee_name', '').strip()
        employee_email = request.POST.get('employee_email', '').strip()
        department = request.POST.get('department', '').strip()
        reason = request.POST.get('reason', '').strip()
        last_working_date = request.POST.get('last_working_date', '') or None

        if not all([request_type, employee_name, employee_email, reason]):
            messages.error(request, 'Please fill in all required fields.')
        else:
            UserRequest.objects.create(
                request_type=request_type,
                employee_name=employee_name,
                employee_email=employee_email,
                department=department,
                reason=reason,
                last_working_date=last_working_date,
                submitted_by=request.user,
            )
            messages.success(request, f'Request submitted to IT Admin.')
            return redirect('hr:user_request_list')

    context = {'request_types': UserRequest.REQUEST_TYPE_CHOICES}
    return render(request, 'hr/user_request_create.html', context)


@login_required
@role_required('ADMIN')
def user_request_action(request, pk):
    user_req = get_object_or_404(UserRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('admin_comment', '').strip()

        if action == 'action':
            user_req.status = 'ACTIONED'
        elif action == 'decline':
            user_req.status = 'DECLINED'

        user_req.admin_comment = comment
        user_req.save()

        messages.success(request, f'Request for {user_req.employee_name} marked as {user_req.status.lower()}.')
        return redirect('hr:user_request_list')

    context = {'user_req': user_req}
    return render(request, 'hr/user_request_action.html', context)

# ── LETTER REQUESTS ───────────────────────────────────────────────

@login_required
def letter_request_create(request):
    """Any employee can request a confirmation letter."""
    if request.method == 'POST':
        salutation = request.POST.get('salutation')
        employee_id_number = request.POST.get('employee_id_number', '')
        job_title = request.POST.get('job_title', '').strip()
        plot_number = request.POST.get('plot_number', '')
        ward = request.POST.get('ward', '')
        po_box = request.POST.get('po_box', '')
        postal_city = request.POST.get('postal_city', 'Gaborone')
        purpose = request.POST.get('purpose', '')

        if not all([salutation, job_title]):
            messages.error(request, 'Salutation and job title are required.')
        else:
            from .models import LetterRequest
            LetterRequest.objects.create(
                requested_by=request.user,
                salutation=salutation,
                employee_id_number=employee_id_number,
                job_title=job_title,
                plot_number=plot_number,
                ward=ward,
                po_box=po_box,
                postal_city=postal_city,
                purpose=purpose,
            )
            messages.success(request, 'Your confirmation letter request has been submitted to HR.')
            return redirect('hr:my_letter_requests')

    from .models import LetterRequest
    context = {
        'salutation_choices': LetterRequest.SALUTATION_CHOICES,
    }
    return render(request, 'hr/letter_request_create.html', context)


@login_required
def my_letter_requests(request):
    """Employee views their own letter requests."""
    from .models import LetterRequest
    requests_qs = LetterRequest.objects.filter(requested_by=request.user)
    context = {'requests': requests_qs}
    return render(request, 'hr/my_letter_requests.html', context)


@login_required
@role_required('HR', 'ADMIN')
def letter_request_list(request):
    """HR views all pending letter requests."""
    from .models import LetterRequest
    pending = LetterRequest.objects.filter(status='PENDING').order_by('requested_at')
    completed = LetterRequest.objects.filter(status='COMPLETED').order_by('-actioned_at')
    context = {'pending': pending, 'completed': completed}
    return render(request, 'hr/letter_request_list.html', context)


@login_required
@role_required('HR', 'ADMIN')
def letter_request_complete(request, pk):
    """HR completes a letter request by adding salary and generating the PDF."""
    from .models import LetterRequest
    from django.utils import timezone
    letter_req = get_object_or_404(LetterRequest, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'decline':
            letter_req.status = 'DECLINED'
            letter_req.hr_notes = request.POST.get('hr_notes', '')
            letter_req.actioned_by = request.user
            letter_req.actioned_at = timezone.now()
            letter_req.save()
            messages.success(request, f'Request from {letter_req.requested_by.get_full_name()} declined.')
            return redirect('hr:letter_request_list')

        annual_salary = request.POST.get('annual_salary', '')
        hr_notes = request.POST.get('hr_notes', '')

        try:
            hr_profile = HRProfile.objects.get(is_active=True)
        except HRProfile.DoesNotExist:
            messages.error(request, 'No active HR profile found. Please set up an HR profile first.')
            return redirect('hr:letter_request_list')

        # Create the ConfirmationLetter record
        letter = ConfirmationLetter.objects.create(
            employee=letter_req.requested_by,
            salutation=letter_req.salutation,
            employee_id_number=letter_req.employee_id_number,
            job_title=letter_req.job_title,
            annual_salary=annual_salary if annual_salary else None,
            plot_number=letter_req.plot_number,
            ward=letter_req.ward,
            po_box=letter_req.po_box,
            postal_city=letter_req.postal_city,
            purpose=letter_req.purpose,
            created_by=request.user,
        )

        # Link back to the request and mark complete
        letter_req.annual_salary = annual_salary if annual_salary else None
        letter_req.hr_notes = hr_notes
        letter_req.actioned_by = request.user
        letter_req.actioned_at = timezone.now()
        letter_req.status = 'COMPLETED'
        letter_req.confirmation_letter = letter
        letter_req.save()

        messages.success(
            request,
            f'Letter for {letter_req.requested_by.get_full_name()} completed. They can now download it.'
        )
        return redirect('hr:letter_request_list')

    context = {'letter_req': letter_req}
    return render(request, 'hr/letter_request_complete.html', context)


# SECTION 2 — add to hr/views.py
# ----------------------------------------------------------------
# Add StudyBondRequest to the existing model import if not already
# there (it should be, from the earlier step), then append:
@login_required
def study_bond_request_create(request):
    """Any employee can apply for a Study Bond."""
    if request.method == 'POST':
        department_type = request.POST.get('department_type')
        assigned_pi_id = request.POST.get('assigned_pi', '')
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        program_title = request.POST.get('program_title', '').strip()
        institution = request.POST.get('institution', '').strip()
        total_cost = request.POST.get('total_cost', '')
        subject_costs = request.POST.get('subject_costs', '')
        amount_paid_by_bup = request.POST.get('amount_paid_by_bup', '')
        payment_date = request.POST.get('payment_date') or None
        payment_receipt = request.FILES.get('payment_receipt')
 
        errors = []
        if not all([department_type, period_start, period_end, program_title,
                    institution, total_cost, subject_costs, amount_paid_by_bup]):
            errors.append('Please fill in all required fields.')
        if department_type == 'RESEARCH' and not assigned_pi_id:
            errors.append('Please select the PI responsible for approving this request.')
 
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            StudyBondRequest.objects.create(
                requested_by=request.user,
                department_type=department_type,
                assigned_pi_id=assigned_pi_id or None,
                period_start=period_start,
                period_end=period_end,
                program_title=program_title,
                institution=institution,
                total_cost=total_cost,
                subject_costs=subject_costs,
                amount_paid_by_bup=amount_paid_by_bup,
                payment_date=payment_date,
                payment_receipt=payment_receipt,
            )
            messages.success(request, 'Your Study Bond request has been submitted for approval.')
            return redirect('hr:my_study_bond_requests')
 
    context = {
        'department_choices': StudyBondRequest.DEPARTMENT_TYPE_CHOICES,
        'pi_choices': CustomUser.objects.filter(role='PI', is_archived=False, is_active=True),
    }
    return render(request, 'hr/study_bond_request_create.html', context)
 
 
@login_required
def my_study_bond_requests(request):
    """Employee views their own Study Bond requests."""
    requests_qs = StudyBondRequest.objects.filter(requested_by=request.user)
    return render(request, 'hr/my_study_bond_requests.html', {'requests': requests_qs})
 
 
@login_required
@role_required('HR', 'DIRECTOR', 'PI', 'ADMIN')
def study_bond_approval_queue(request):
    """Shows only what THIS user is responsible for actioning."""
    role = request.user.role
 
    pending_hr_review = StudyBondRequest.objects.none()
    pending_registration = StudyBondRequest.objects.none()
    pending_grade = StudyBondRequest.objects.none()
 
    if role in ('HR', 'ADMIN'):
        pending_hr_review = StudyBondRequest.objects.filter(status='PENDING_HR_REVIEW')
 
    if role == 'ADMIN':
        pending_registration = StudyBondRequest.objects.filter(status='PENDING')
        pending_grade = StudyBondRequest.objects.filter(status='REGISTERED')
    elif role == 'DIRECTOR':
        pending_registration = StudyBondRequest.objects.filter(status='PENDING', department_type='OPERATIONS')
        pending_grade = StudyBondRequest.objects.filter(status='REGISTERED', department_type='OPERATIONS')
    elif role == 'PI':
        pending_registration = StudyBondRequest.objects.filter(
            status='PENDING', department_type='RESEARCH', assigned_pi=request.user)
        pending_grade = StudyBondRequest.objects.filter(
            status='REGISTERED', department_type='RESEARCH', assigned_pi=request.user)
 
    context = {
        'pending_hr_review': pending_hr_review,
        'pending_registration': pending_registration,
        'pending_grade': pending_grade,
    }
    return render(request, 'hr/study_bond_approval_queue.html', context)
 
 
@login_required
def study_bond_action(request, pk):
    """
    Single view for all three stages: PENDING_HR_REVIEW (HR verifies salary
    and the cap), PENDING (Director/PI approve/decline-to-register), and
    REGISTERED (grade verification). The template branches on sb.status.
    """
    sb = get_object_or_404(StudyBondRequest, pk=pk)
 
    if not sb.can_be_actioned_by(request.user):
        return redirect('accounts:access_denied')
 
    if request.method == 'POST':
        if sb.status == 'PENDING_HR_REVIEW':
            action = request.POST.get('action')
            notes = request.POST.get('hr_notes', '')
            if action == 'forward':
                salary = request.POST.get('hr_verified_salary', '')
                cap_amount = request.POST.get('hr_cap_amount', '')
                if not salary or not cap_amount:
                    messages.error(request, 'Please enter the verified salary and cap amount.')
                    return redirect('hr:study_bond_action', pk=pk)
                sb.hr_review_forward(request.user, salary, cap_amount, notes)
                messages.success(request, 'Study Bond registered.')
            elif action == 'decline':
                sb.hr_review_decline(request.user, notes)
                messages.success(request, 'Study Bond declined at HR review.')
        elif sb.status == 'PENDING':
            action = request.POST.get('action')
            if action == 'approve':
                sb.approve_registration(request.user)
                messages.success(
                    request,
                    f"{sb.requested_by.get_full_name()}'s Study Bond approved — forwarded to HR to finalize."
                )
            elif action == 'decline':
                sb.decline_registration(request.user, request.POST.get('decline_reason', ''))
                messages.success(request, 'Study Bond declined.')
        elif sb.status == 'REGISTERED':
            grade = request.POST.get('grade_received', '').strip()
            if grade:
                sb.verify_grade(request.user, grade)
                messages.success(request, 'Grade verified — Study Bond completed.')
            else:
                messages.error(request, 'Please enter the grade received.')
 
        return redirect('hr:study_bond_approval_queue')
 
    return render(request, 'hr/study_bond_action.html', {'sb': sb})

@login_required
def study_bond_download(request, pk):
    """
    Downloadable by: HR, Admin, the assigned Director, the assigned PI,
    and the employee who requested it. Works at any stage — a still-
    PENDING bond downloads with blank approval fields, useful as a
    printable record of what was submitted.
    """
    sb = get_object_or_404(StudyBondRequest, pk=pk)
    user = request.user
 
    allowed = (
        user.role in ('HR', 'ADMIN')
        or user == sb.requested_by
        or (user.role == 'DIRECTOR' and sb.department_type == 'OPERATIONS')
        or (user.role == 'PI' and sb.assigned_pi_id == user.id)
    )
    if not allowed:
        return redirect('accounts:access_denied')
 
    from .pdf_utils import generate_study_bond_pdf
    pdf_buffer = generate_study_bond_pdf(sb, request)
 
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"Study_Bond_{sb.requested_by.get_full_name().replace(' ', '_')}_{sb.pk}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
 
 