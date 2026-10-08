"""
The emailed link for a new employee, who has no account. The secret in it is random and goes only to
the address HR typed. Only its hash is stored. It works for several visits (the form is long) until it
is submitted, replaced, closed, or expires.
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
    return int(getattr(settings, 'ONBOARDING_LINK_DAYS', 30))


def link_url(raw):
    base = getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000').rstrip('/')
    return base + reverse('onboarding:form', args=[raw])


def issue_link(req):
    """Give the request a new link, replacing any earlier one. Returns the secret for the email."""
    raw = secrets.token_urlsafe(32)
    req.token_hash = hash_token(raw)
    req.token_expires_at = timezone.now() + timedelta(days=link_days())
    req.save()
    return raw


def revoke_link(req):
    req.token_hash = ''
    req.token_expires_at = None
    req.save()


def find_request(raw):
    """The request a link belongs to, or None for anything wrong: unknown, replaced, expired, submitted or closed."""
    if not raw or len(raw) > 200:
        return None
    from .models import PersonalDetailsRequest
    req = PersonalDetailsRequest.objects.filter(token_hash=hash_token(raw)).first()
    if req is None or not req.token_hash or req.status != 'SENT':
        return None
    if req.token_expires_at is None or req.token_expires_at <= timezone.now():
        return None
    return req
