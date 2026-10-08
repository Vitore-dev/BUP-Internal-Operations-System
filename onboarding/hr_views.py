"""HR's pages: send the form, see what came back, download it, send it back, close it, delete it."""

import datetime as dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from core.utils import log_action
from . import workflow
from .models import PersonalDetailsDocument, PersonalDetailsRequest
from .workflow import WorkflowError

S = PersonalDetailsRequest.Status


@login_required
@role_required('HR', 'ADMIN')
def hr_list(request):
    wanted = request.GET.get('status', '')
    everything = list(PersonalDetailsRequest.objects.all())
    shown = [r for r in everything if not wanted or r.status == wanted]
    counts = {value: sum(1 for r in everything if r.status == value) for value, _ in S.choices}
    return render(request, 'onboarding/hr_list.html', {
        'requests': shown, 'wanted': wanted, 'total': len(everything),
        'status_counts': [(value, label, counts[value]) for value, label in S.choices]})


@login_required
@role_required('HR', 'ADMIN')
def hr_new(request):
    if request.method == 'POST':
        assumption = None
        raw = (request.POST.get('assumption_date') or '').strip()
        try:
            if raw:
                assumption = dt.date.fromisoformat(raw)
            req = workflow.create_request(request.user, request.POST.get('recipient_name'), request.POST.get('recipient_email'),
                                          request.POST.get('position_title'), request.POST.get('program'), assumption)
        except ValueError:
            messages.error(request, 'The start date is not a valid date.')
        except WorkflowError as error:
            messages.error(request, str(error))
        else:
            log_action(request, 'PERSONAL_DETAILS_SENT', description=f'{request.user} sent the personal details form to {req.recipient_name} <{req.recipient_email}> (#{req.pk}).')
            messages.success(request, f'The form was emailed to {req.recipient_name}.')
            return redirect('onboarding:hr_detail', pk=req.pk)
        return render(request, 'onboarding/hr_new.html', {'values': request.POST})
    return render(request, 'onboarding/hr_new.html', {'values': {}})


@login_required
@role_required('HR', 'ADMIN')
def hr_detail(request, pk):
    req = get_object_or_404(PersonalDetailsRequest, pk=pk)
    if req.status == S.SUBMITTED or req.submitted_at:
        # a record of every time someone opens a form that holds ID and bank details
        log_action(request, 'PERSONAL_DETAILS_VIEWED', description=f'{request.user} opened the personal details of {req.recipient_name} (#{req.pk}).')
    return render(request, 'onboarding/hr_detail.html', {'req': req, 'documents': req.documents.all(), 'has_data': bool(req.submitted_at)})


@login_required
@role_required('HR', 'ADMIN')
def hr_action(request, pk):
    req = get_object_or_404(PersonalDetailsRequest, pk=pk)
    if request.method != 'POST':
        return redirect('onboarding:hr_detail', pk=pk)
    action = request.POST.get('action')
    try:
        if action == 'resend':
            workflow.resend(req)
            messages.success(request, 'A fresh link was emailed. The old one no longer works.')
        elif action == 'reopen':
            workflow.reopen(req, request.POST.get('note'))
            log_action(request, 'PERSONAL_DETAILS_REOPENED', description=f'{request.user} sent the form of {req.recipient_name} back for corrections (#{req.pk}).')
            messages.success(request, 'Sent back. The new employee was emailed a fresh link, and their answers are still filled in.')
        elif action == 'close':
            workflow.close(req)
            log_action(request, 'PERSONAL_DETAILS_CLOSED', description=f'{request.user} closed the form for {req.recipient_name} (#{req.pk}).')
            messages.success(request, 'The form was closed. Its link no longer works.')
        else:
            messages.error(request, 'Unknown action.')
    except WorkflowError as error:
        messages.error(request, str(error))
    return redirect('onboarding:hr_detail', pk=pk)


@login_required
@role_required('HR', 'ADMIN')
def hr_pdf(request, pk):
    from .pdf import generate_personal_details_pdf
    req = get_object_or_404(PersonalDetailsRequest, pk=pk)
    log_action(request, 'PERSONAL_DETAILS_PDF', description=f'{request.user} downloaded the personal details PDF of {req.recipient_name} (#{req.pk}).')
    response = HttpResponse(generate_personal_details_pdf(req).getvalue(), content_type='application/pdf')
    name = ''.join(c if c.isalnum() else '_' for c in req.recipient_name).strip('_') or 'employee'
    response['Content-Disposition'] = f'attachment; filename="Personal_Details_{name}_{req.pk}.pdf"'
    return response


@login_required
@role_required('HR', 'ADMIN')
def hr_document(request, pk, doc_pk):
    """The only way to reach an attached file: through here, for HR, and recorded."""
    doc = get_object_or_404(PersonalDetailsDocument, pk=doc_pk, request_id=pk)
    log_action(request, 'PERSONAL_DETAILS_DOCUMENT', description=f'{request.user} downloaded "{doc.original_name}" for {doc.request.recipient_name} (#{pk}).')
    response = FileResponse(doc.file.open('rb'), as_attachment=True, filename=doc.original_name)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@role_required('HR', 'ADMIN')
def hr_delete(request, pk):
    """Permanently remove a form, its answers and its attached files. A GET only shows the confirmation."""
    req = get_object_or_404(PersonalDetailsRequest, pk=pk)
    if request.method == 'POST':
        name, docs = req.recipient_name, list(req.documents.all())
        files = [(d.file.storage, d.file.name) for d in docs if d.file]
        with transaction.atomic():
            req.documents.all().delete()
            req.delete()
        removed = 0
        for storage, filename in files:
            try:
                storage.delete(filename)
                removed += 1
            except Exception:
                pass
        log_action(request, 'PERSONAL_DETAILS_DELETED', description=f'{request.user} permanently deleted the personal details form of {name} (#{pk}): {len(docs)} document(s), {removed} file(s) removed from disk.')
        messages.success(request, f'The form for {name} was deleted for good.')
        return redirect('onboarding:hr_list')
    return render(request, 'onboarding/hr_delete.html', {'req': req, 'document_count': req.documents.count()})
