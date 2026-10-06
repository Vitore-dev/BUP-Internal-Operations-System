"""
One switch for every notification in the system.

Views call notify() at each workflow step. For Study Bond events the message
is built in employee_services/study_bond_emails.py and sent through
core/mailer.py (Microsoft Graph). No view needs to know how email works, and
a failure here can never break a workflow step.

Usage:
    from core.notifications import notify
    notify('study_bond_approved', recipient=application.employee, context={'application': application})
"""

import logging

logger = logging.getLogger('core.notifications')


def notify(event, recipient, context=None):
    context = context or {}
    logger.info(
        "notify: event=%s recipient=%s context_keys=%s",
        event, getattr(recipient, 'username', recipient), list(context.keys()),
    )
    try:
        specs = []
        if event.startswith('study_bond_'):
            # imported here, not at the top, so core never depends on employee_services at import time
            from employee_services.study_bond_emails import emails_for
            specs = emails_for(event, recipient, context)

        results = []
        if specs:
            from .mailer import send_email
            for spec in specs:
                results.append(send_email(event=event, **spec))
        return results
    except Exception:
        logger.exception("notify failed for event %s (the workflow step itself is unaffected)", event)
        return []

