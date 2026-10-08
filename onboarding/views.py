"""The new employee's form (a private emailed link, no sign-in) and thank-you page."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from core.utils import get_client_ip, log_action
from . import workflow
from .links import find_request
from .models import PersonalDetailsDocument, PersonalDetailsRequest
from .validation import DOC_KINDS, validate_submission, validate_uploads
from .workflow import WorkflowError

FIELDS = ['full_names', 'date_of_birth', 'gender', 'marital_status', 'id_number', 'id_expiry', 'postal_address', 'physical_address', 'telephone',
          'assumption_date', 'position_title', 'email_address', 'program', 'kin_name', 'kin_relationship', 'kin_telephone', 'emergency_name',
          'emergency_telephone', 'emergency_relationship', 'qualifications', 'bank_name', 'bank_branch_code', 'bank_branch_name',
          'bank_account_number', 'bank_account_name', 'declaration_name']


def _public(request, template, context, status=200):
    response = render(request, template, context, status=status)
    # 'same-origin', never 'no-referrer': that makes browsers send "Origin: null" on form posts, which Django's CSRF check rejects.
    response['Referrer-Policy'] = 'same-origin'
    return response


def _initial(req):
    """What to show in the form at first: anything already saved, else what HR knew."""
    values = {f: getattr(req, f) for f in FIELDS}
    values['full_names'] = values['full_names'] or req.recipient_name
    values['email_address'] = values['email_address'] or req.recipient_email
    for f in ('date_of_birth', 'id_expiry', 'assumption_date'):
        values[f] = values[f].isoformat() if values[f] else ''
    return values


@never_cache
def form(request, token):
    req = find_request(token)
    if req is None:
        return _public(request, 'onboarding/public/invalid.html', {}, status=404)

    context = {'req': req, 'token': token, 'kinds': PersonalDetailsDocument.Kind.choices,
               'genders': PersonalDetailsRequest.GENDER_CHOICES, 'maritals': PersonalDetailsRequest.MARITAL_CHOICES, 'errors': {}, 'upload_errors': []}

    if request.method == 'POST':
        clean, errors = validate_submission(request.POST)
        files = {k: request.FILES.getlist(f'doc_{k}') for k in DOC_KINDS}
        files = {k: v for k, v in files.items() if v}
        upload_errors = validate_uploads(files)
        if errors or upload_errors:
            context.update({'values': request.POST, 'errors': errors, 'upload_errors': upload_errors})
            return _public(request, 'onboarding/public/form.html', context)
        try:
            workflow.submit(req, clean, files, get_client_ip(request))
        except WorkflowError as error:
            messages.error(request, str(error))
            return redirect('onboarding:form', token=token)
        log_action(request, 'PERSONAL_DETAILS_SUBMITTED', description=f'{req.recipient_name} submitted their personal details form (#{req.pk}).')
        return redirect('onboarding:thanks')

    req.last_used_at = timezone.now()
    req.save()
    context['values'] = _initial(req)
    return _public(request, 'onboarding/public/form.html', context)


@never_cache
def thanks(request):
    return _public(request, 'onboarding/public/thanks.html', {})
