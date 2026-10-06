"""
Who is emailed what, at each Study Bond step.

emails_for() takes the event name (the same names the views pass to notify()),
the recipient the view passed, and the context, and returns a list of messages
ready for core.mailer.send_email(). It only describes the emails; sending,
logging and the test-mode safety rules live in core/mailer.py.

Rules from the plan:
  - Employees get outcome emails only: sent back for changes, approved, declined, paid.
  - HR and Finance staff are emailed individually (everyone with that role, one message to the group).
  - Emails name the person and the program, never salary or amounts.
  - A PI who decides by emailed link is sent the one-time link, at the address HR checked.
    An approver who signs in is sent a plain sign-in link.
"""

import logging
import mimetypes
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from .routing import approver_link_profile

logger = logging.getLogger('employee_services.emails')


def _url(name, *args):
    base = getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000').rstrip('/')
    return base + reverse(name, args=args)


def _name(user):
    return (user.get_full_name() or user.username) if user else 'Someone'


def _address(user):
    return (getattr(user, 'email', '') or '').strip() if user else ''


def _staff_addresses(role):
    users = get_user_model().objects.filter(role=role, is_archived=False, is_active=True).exclude(email='')
    return [u.email for u in users]


def _details(app):
    return [
        ("Employee", _name(app.employee)),
        ("Program", app.program_title),
        ("Institution", app.institution),
        ("Type", app.get_application_type_display()),
    ]


def _message(to, subject, heading, paragraphs, app, button_label=None, button_url=None,
             details=True, attachments=()):
    return {
        'to': to,
        'subject': subject,
        'heading': heading,
        'paragraphs': paragraphs,
        'details': _details(app) if details else [],
        'button_label': button_label,
        'button_url': button_url,
        'attachments': list(attachments),
        'related_id': app.pk,
    }


def _approver_address(approver):
    """Where to reach an approver: a link-PI's checked approval address, otherwise their own email."""
    profile = approver_link_profile(approver)
    return profile.approval_email if profile else _address(approver)


def _paid_attachments(app, include_receipt):
    """The finished Study Bond PDF, plus the payment receipt for the employee. Missing pieces are skipped, never fatal."""
    attachments = []
    try:
        from .pdf_utils import generate_study_bond_pdf
        attachments.append((f"Study_Bond_{app.pk}.pdf", generate_study_bond_pdf(app).getvalue(), 'application/pdf'))
    except Exception:
        logger.exception("Could not build the Study Bond PDF for application %s", app.pk)
    if include_receipt and app.payment_receipt:
        try:
            app.payment_receipt.open('rb')
            data = app.payment_receipt.read()
            app.payment_receipt.close()
            name = os.path.basename(app.payment_receipt.name)
            attachments.append((name, data, mimetypes.guess_type(name)[0] or 'application/octet-stream'))
        except Exception:
            logger.exception("Could not read the receipt for application %s", app.pk)
    return attachments


def emails_for(event, recipient, ctx):
    app = ctx.get('application')
    if app is None:
        return []
    employee = _name(app.employee)
    continuation = app.is_continuation()
    kind = "continuation request" if continuation else "application"
    view_url = _url('employee_services:study_bond_detail', app.pk)
    messages = []

    # ── employee submitted -> HR is asked to review ─────────────────────
    if event in ('study_bond_submitted', 'study_bond_continuation_submitted'):
        messages.append(_message(
            _staff_addresses('HR'), f"Study Bond {kind} to review: {employee}",
            "A Study Bond application is waiting for HR review",
            [f"{employee} has submitted a Study Bond {kind} for {app.program_title}.",
             "Please check the attachments and verify the costs."],
            app, "Review application", _url('employee_services:study_bond_hr_review', app.pk)))

    # ── HR sent it back -> the employee is told what to fix ─────────────
    elif event == 'study_bond_returned':
        reason = ctx.get('reason') or (app.latest_return.reason if app.latest_return else '')
        messages.append(_message(
            [_address(recipient)], "Your Study Bond application needs changes",
            "HR has sent your application back",
            [f"HR reviewed your application for {app.program_title} and needs you to make some changes.",
             f"Note from HR: {reason}",
             "You can edit your application and send it back, or withdraw it."],
            app, "Edit and resubmit", _url('employee_services:study_bond_edit', app.pk), details=False))

    # ── the employee fixed it and resubmitted -> HR reviews again ───────
    elif event == 'study_bond_resubmitted':
        messages.append(_message(
            _staff_addresses('HR'), f"Study Bond application resubmitted (round {app.round_number}): {employee}",
            "A returned application has been resubmitted",
            [f"{employee} has made changes to their application for {app.program_title} and sent it back for review.",
             f"This is round {app.round_number}."],
            app, "Review application", _url('employee_services:study_bond_hr_review', app.pk)))

    # ── HR finished -> the approver is asked to decide ──────────────────
    elif event == 'study_bond_pending_approval':
        if recipient is None:
            return []
        if ctx.get('approval_link'):
            # an approver who does not sign in: one-time link, to the address HR checked
            profile = approver_link_profile(recipient)
            if profile is None:
                return []
            expires = ctx.get('link_expires')
            expiry = f"The link works once and expires on {expires:%d %B %Y}." if expires else "The link works once and expires after a few days."
            prefix = "Reminder: " if ctx.get('resend') else ""
            messages.append(_message(
                [profile.approval_email], f"{prefix}Study Bond approval needed: {employee}",
                "An application needs your decision",
                [f"Dear {profile.display_name},",
                 f"HR has finished reviewing {employee}'s Study Bond application for {app.program_title}.",
                 "Please open the link below to see the application and its attachments and give your decision. You do not need to sign in.",
                 expiry],
                app, "Review application", ctx['approval_link']))
        else:
            if not getattr(recipient, 'azure_id', None):
                logger.info("Approver %s has not signed in and has no approval link; nothing emailed.", _name(recipient))
                return []
            messages.append(_message(
                [_address(recipient)], f"Study Bond approval needed: {employee}",
                "An application needs your decision",
                [f"HR has finished reviewing {employee}'s application for {app.program_title}.",
                 "Please review the details and attachments, then approve or decline."],
                app, "Review and decide", _url('employee_services:study_bond_approver_review', app.pk)))

    # ── approved -> employee told, Finance asked to pay ─────────────────
    elif event == 'study_bond_approved':
        messages.append(_message(
            [_address(recipient)], "Your Study Bond application was approved",
            "Your application has been approved",
            [f"Your application for {app.program_title} at {app.institution} has been approved.",
             "It has been passed to Finance for payment. You will get another email when the payment is processed."],
            app, "View application", view_url, details=False))
        messages.append(_message(
            _staff_addresses('FINANCE'), f"Study Bond payment waiting: {employee}",
            "An approved application is ready for payment",
            [f"{employee}'s application for {app.program_title} has been approved."],
            app, "Process payment", _url('employee_services:study_bond_finance_process', app.pk)))

    # ── declined by the approver -> employee told (with the reason), HR informed ──
    elif event == 'study_bond_declined':
        reason = [f"Reason: {app.decline_reason}"] if app.decline_reason else []
        messages.append(_message(
            [_address(recipient)], "Your Study Bond application was declined",
            "Your application was not approved",
            [f"Your application for {app.program_title} at {app.institution} was declined."] + reason,
            app, "View application", view_url, details=False))
        messages.append(_message(
            _staff_addresses('HR'), f"Study Bond application declined: {employee}",
            "A Study Bond application was declined",
            [f"The application for {app.program_title} was declined by {_name(app.approver)}."] + reason,
            app, "View application", view_url))

    # ── continuation refused at the grade check -> employee told, with HR's note ──
    elif event == 'study_bond_continuation_declined':
        reason = [f"Note from HR: {app.hr_notes}"] if app.hr_notes else []
        messages.append(_message(
            [_address(recipient)], "Your Study Bond continuation was declined",
            "Your continuation request was not approved",
            [f"Your continuation request for {app.program_title} was declined."] + reason,
            app, "View application", view_url, details=False))

    # ── the employee withdrew -> HR told, and the approver if they already had it ──
    elif event == 'study_bond_withdrawn':
        why = [f"Reason given: {app.withdrawn_reason}"] if app.withdrawn_reason else []
        messages.append(_message(
            _staff_addresses('HR'), f"Study Bond application withdrawn: {employee}",
            "A Study Bond application was withdrawn",
            [f"{employee} has withdrawn their application for {app.program_title}."] + why,
            app, "View application", view_url))
        if ctx.get('notify_approver') and app.approver:
            messages.append(_message(
                [_approver_address(app.approver)], f"Study Bond application withdrawn: {employee}",
                "You no longer need to decide on this application",
                [f"{employee} has withdrawn their application for {app.program_title}.",
                 "Nothing more is needed from you, and any approval link you were sent has stopped working."],
                app))

    # ── payment processed -> employee gets the form and receipt, HR gets the form ──
    elif event == 'study_bond_paid':
        if recipient is None:
            return []
        if recipient.pk == app.employee_id:
            attachments = _paid_attachments(app, include_receipt=True)
            attached = "The finished Study Bond form is attached." if attachments else "You can download the finished form from the application page."
            if len(attachments) > 1:
                attached = "The finished Study Bond form and your payment receipt are attached."
            messages.append(_message(
                [_address(recipient)], "Your Study Bond payment has been processed",
                "Your payment has been processed",
                [f"Finance has processed the payment for your Study Bond for {app.program_title}.", attached],
                app, "View application", view_url, details=False, attachments=attachments))
        else:
            attachments = _paid_attachments(app, include_receipt=False)
            messages.append(_message(
                [_address(recipient)], f"Study Bond payment processed: {employee}",
                "A Study Bond payment has been processed",
                [f"Finance has processed the payment for {employee}'s Study Bond for {app.program_title}.",
                 "The finished Study Bond form is attached." if attachments else "The finished form is on the application page."],
                app, "View application", view_url, attachments=attachments))

    return messages
