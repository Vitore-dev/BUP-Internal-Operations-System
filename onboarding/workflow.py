"""
Every step of a personal details form and the rules for each. The pages collect input and call these
functions; each checks the state, raises WorkflowError with a plain message if something is wrong,
changes the request, and sends the emails. Nothing here knows about web pages.

  SENT (HR emailed the link)  ->  SUBMITTED (the employee filled it in, it is with HR)
  HR can: resend the link, send it back for corrections (-> SENT), close it, or delete it for good.
"""

import re

from django.db import transaction
from django.utils import timezone

from core.notifications import notify
from .links import find_request, issue_link, link_url, revoke_link
from .models import PersonalDetailsDocument, PersonalDetailsRequest

S = PersonalDetailsRequest.Status
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class WorkflowError(Exception):
    """Something is missing or not allowed. The message is shown as written."""


def _move(req, status):
    req.status = status
    req.status_changed_at = timezone.now()
    req.save()


def create_request(created_by, name, email, position='', program='', assumption_date=None):
    """HR sends the form to someone new. Emails them their link."""
    name = (name or '').strip()
    email = (email or '').strip().lower()
    if not name:
        raise WorkflowError("Please give the new employee's name.")
    if not EMAIL_RE.match(email):
        raise WorkflowError("Please give a valid email address for the new employee.")
    if PersonalDetailsRequest.objects.filter(recipient_email=email, status=S.SENT).first():
        raise WorkflowError("A form has already been sent to this address and is waiting to be filled in. Use 'Send the link again' on it instead.")
    req = PersonalDetailsRequest.objects.create(
        created_by=created_by, recipient_name=name, recipient_email=email, position_title=(position or '').strip(),
        program=(program or '').strip(), assumption_date=assumption_date)
    raw = issue_link(req)
    notify('onboarding_invite', recipient=None, context={'req': req, 'link': link_url(raw)})
    return req


def resend(req):
    """A fresh link for someone who has not filled the form in yet. The old link stops working."""
    if req.status != S.SENT:
        raise WorkflowError('This form is no longer waiting for the new employee.')
    raw = issue_link(req)
    notify('onboarding_invite', recipient=None, context={'req': req, 'link': link_url(raw), 'resend': True})


def submit(req, clean, files_by_kind, ip):
    """
    The new employee sends their details in. `clean` is validate_submission's result (already checked),
    files_by_kind is {kind: [uploaded files]} (already checked). The link dies the moment this succeeds.
    """
    if req.status != S.SENT:
        raise WorkflowError('This form has already been submitted.')
    with transaction.atomic():
        for field, value in clean.items():
            setattr(req, field, value)
        req.declaration_ip = ip
        req.submitted_at = timezone.now()
        req.reopen_note = ''
        req.save()
        for kind, files in files_by_kind.items():
            for f in files:
                PersonalDetailsDocument.objects.create(request=req, kind=kind, file=f, original_name=(f.name or 'file')[:255], size=f.size)
        _move(req, S.SUBMITTED)
        revoke_link(req)
    notify('onboarding_submitted', recipient=None, context={'req': req})
    notify('onboarding_received', recipient=None, context={'req': req})


def reopen(req, note):
    """HR sends it back for corrections: a fresh link, the same answers still filled in."""
    if req.status != S.SUBMITTED:
        raise WorkflowError('Only a submitted form can be sent back.')
    note = (note or '').strip()
    if not note:
        raise WorkflowError('Please say what the new employee needs to correct.')
    req.reopen_note = note
    _move(req, S.SENT)
    raw = issue_link(req)
    notify('onboarding_reopened', recipient=None, context={'req': req, 'link': link_url(raw)})


def close(req):
    """Cancel a form that will not be filled in. The link stops working."""
    if req.status == S.CLOSED:
        raise WorkflowError('This form is already closed.')
    _move(req, S.CLOSED)
    revoke_link(req)
