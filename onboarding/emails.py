"""
Who is emailed what. Builders only; sending and logging live in core/mailer.py. An email names the new
employee and says what is needed. It NEVER contains anything they filled in: no ID numbers, no bank
details, no addresses.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

logger = logging.getLogger('onboarding.emails')


def _base():
    return getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000').rstrip('/')


def _days():
    return int(getattr(settings, 'ONBOARDING_LINK_DAYS', 30))


def _hr_addresses():
    users = get_user_model().objects.filter(role='HR', is_archived=False, is_active=True).exclude(email='')
    return [u.email for u in users]


def _spec(to, subject, heading, paragraphs, req, label=None, url=None):
    return {'to': list(to), 'subject': subject, 'heading': heading, 'paragraphs': list(paragraphs),
            'details': [("New employee", req.recipient_name)], 'button_label': label, 'button_url': url,
            'attachments': [], 'related_id': req.pk}


def emails_for(event, recipient, ctx):
    req = ctx.get('req')
    if req is None:
        return []
    link = ctx.get('link')
    prefix = 'Reminder: ' if ctx.get('resend') else ''

    if event == 'onboarding_invite':
        return [_spec([req.recipient_email], f"{prefix}Welcome to BUP: please complete your personal details form",
                      "Please complete your personal details form",
                      [f"Dear {req.recipient_name},",
                       "Welcome to the Botswana-UPenn Partnership. Before you start, HR needs some personal details from you.",
                       "Please have ready: a copy of your passport or Omang, your bank details, and any qualification or certificate copies you wish to attach.",
                       f"The link below is private to you and works for {_days()} days. Please do not forward it."],
                      req, "Fill in the form", link)]

    if event == 'onboarding_submitted':
        to = _hr_addresses()
        if not to:
            return []
        return [_spec(to, f"New starter form submitted: {req.recipient_name}", "A personal details form has been submitted",
                      [f"{req.recipient_name} has filled in their personal details form. It is waiting for HR in the system.",
                       "For privacy the details are not included in this email."],
                      req, "Open in the system", _base() + reverse('onboarding:hr_detail', args=[req.pk]))]

    if event == 'onboarding_received':
        return [_spec([req.recipient_email], "We have received your personal details", "Thank you",
                      [f"Dear {req.recipient_name},", "HR has received your personal details form. You do not need to do anything more."], req)]

    if event == 'onboarding_reopened':
        return [_spec([req.recipient_email], "HR needs you to correct your personal details form", "Please correct your form",
                      [f"Dear {req.recipient_name},", "HR has sent your form back so something can be corrected.",
                       f"Note from HR: {req.reopen_note}",
                       f"Your earlier answers are still there. The new link works for {_days()} days."],
                      req, "Open the form", link)]
    return []
