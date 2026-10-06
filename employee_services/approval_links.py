"""
One-time approval links for approvers who do not sign in.

The secret in a link is random and is shown to nobody but the person it is
emailed to. Only its SHA-256 hash is stored, so a copy of the database cannot be
turned into working links. A link works once, expires (7 days by default), and
stops working if it is resent, revoked, or the application moves on.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone


def hash_token(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def link_days():
    return int(getattr(settings, 'APPROVAL_LINK_DAYS', 7))


def link_url(raw):
    base = getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000').rstrip('/')
    return base + reverse('employee_services:link_review', args=[raw])


def revoke_links(application):
    """Kill every link for this application that has not been used yet."""
    from .models import ApprovalToken
    ApprovalToken.objects.filter(
        application=application, used_at__isnull=True, revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


def issue_link(application, profile):
    """
    Cancel any earlier links and create a new one addressed to the PI's
    checked approval email. Returns (the secret to put in the email, the stored row).
    """
    from .models import ApprovalToken
    revoke_links(application)
    raw = secrets.token_urlsafe(32)
    now = timezone.now()
    token = ApprovalToken.objects.create(
        application=application,
        approver=application.approver,
        token_hash=hash_token(raw),
        sent_to=profile.approval_email,
        expires_at=now + timedelta(days=link_days()),
    )
    return raw, token


def token_is_usable(token, now=None):
    """
    A link is only good while ALL of these hold: not used, not revoked, not expired,
    the application still waits for an approval, and it still belongs to this approver.
    """
    now = now or timezone.now()
    application = token.application
    return (
        token.used_at is None
        and token.revoked_at is None
        and token.expires_at > now
        and application.status == 'PENDING_APPROVAL'
        and application.approver_id == token.approver_id
    )


def find_active_token(raw):
    """Look a link up by its secret. Returns the row, or None for anything wrong (unknown, used, expired...)."""
    if not raw or len(raw) > 200:
        return None
    from .models import ApprovalToken
    token = (ApprovalToken.objects.select_related('application', 'approver')
             .filter(token_hash=hash_token(raw)).first())
    if token is None or not token_is_usable(token):
        return None
    return token


def latest_token(application):
    return application.approval_tokens.order_by('-created_at').first()
