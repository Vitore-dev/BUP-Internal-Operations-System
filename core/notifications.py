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

# event name prefix -> the module that builds those emails
EMAIL_BUILDERS = {
    'study_bond_': 'employee_services.study_bond_emails',
    'review_': 'reviews.emails',
    'onboarding_': 'onboarding.emails',
}


def notify(event, recipient, context=None):
    context = context or {}
    logger.info(
        "notify: event=%s recipient=%s context_keys=%s",
        event, getattr(recipient, 'username', recipient), list(context.keys()),
    )
    try:
        specs = []
        # Each feature's email builders, found by the start of the event name. Imported only when
        # that kind of event happens, so core never depends on an app that is not installed.
        for prefix, module in EMAIL_BUILDERS.items():
            if event.startswith(prefix):
                import importlib
                specs = importlib.import_module(module).emails_for(event, recipient, context)
                break

        results = []
        if specs:
            from .mailer import send_email
            for spec in specs:
                results.append(send_email(event=event, **spec))
        return results
    except Exception:
        logger.exception("notify failed for event %s (the workflow step itself is unaffected)", event)
        return []

