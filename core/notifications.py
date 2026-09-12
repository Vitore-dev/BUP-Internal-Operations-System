"""
Notification stub.

Email integration is explicitly deferred. Every point in a workflow that
*would* eventually send an email — approver notified of a new application,
employee notified of a status change, HR notified of a pending review —
calls notify() now instead of doing nothing. When email is built (likely
Microsoft Graph, given GRAPH_SENDER_EMAIL already exists in settings.py),
only this file changes. No view that calls notify() needs to be touched.

Usage:
    from core.notifications import notify
    notify('study_bond_submitted', recipient=application.approver, context={
        'application': application,
    })
"""

import logging

logger = logging.getLogger('core.notifications')


def notify(event, recipient, context=None):
    """
    event: short string identifying what happened, e.g. 'study_bond_submitted',
           'study_bond_approved', 'study_bond_declined', 'profile_incomplete_reminder'.
    recipient: the CustomUser who would receive the notification.
    context: dict of whatever the eventual email template will need
             (e.g. {'application': application, 'actor': request.user}).

    Today: logs the event so it's visible in application logs and easy to
    grep for once email is being built, without touching the database twice
    for something the caller's view has likely already written to AuditLog.

    Later: this becomes the single place that renders an email template and
    sends via Microsoft Graph, using GRAPH_SENDER_EMAIL from settings.
    """
    context = context or {}
    logger.info(
        "notify: event=%s recipient=%s context_keys=%s",
        event,
        getattr(recipient, 'username', recipient),
        list(context.keys()),
    )
    # Intentionally a no-op beyond logging until email is implemented.
    return None
