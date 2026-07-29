import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from accounts.decorators import role_required
from accounts.models import CustomUser
from .models import HRForm, ConfirmationLetter, ExtracurricularActivity, UserRequest, HRProfile


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