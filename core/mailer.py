import base64
import json
import logging
import time
from html import escape

import msal
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('core.mailer')

GRAPH = "https://graph.microsoft.com/v1.0"
# Graph accepts roughly 3 MB of attachments in a direct send; stay safely under it.
MAX_ATTACHMENT_BYTES = 2_500_000

_token = {'value': None, 'expires': 0.0}


def _graph_token(force_new=False):
    """Fetch (and briefly reuse) the app's Graph token."""
    if not force_new and _token['value'] and time.time() < _token['expires'] - 60:
        return _token['value']
    cfg = settings.AZURE_AUTH
    app = msal.ConfidentialClientApplication(
        cfg['CLIENT_ID'], authority=cfg['AUTHORITY'], client_credential=cfg['CLIENT_SECRET'],
    )
    result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
    if 'access_token' not in result:
        raise RuntimeError(f"No Graph token: {result.get('error')} {result.get('error_description', '')}".strip())
    _token['value'] = result['access_token']
    _token['expires'] = time.time() + int(result.get('expires_in', 3000))
    return _token['value']


def render_email(heading, paragraphs=(), details=(), button_label=None, button_url=None):
    """
    Build the HTML and plain-text versions of one message. Everything that
    comes from data is escaped, so a program title can never inject markup.
    """
    p_html = "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.55;color:#1E2440;">{escape(p)}</p>' for p in paragraphs
    )
    rows = "".join(
        f'<tr><td style="padding:6px 16px 6px 0;font-size:14px;color:#5A6385;white-space:nowrap;vertical-align:top;">{escape(k)}</td>'
        f'<td style="padding:6px 0;font-size:14px;color:#1E2440;">{escape(str(v))}</td></tr>'
        for k, v in details
    )
    d_html = (f'<table role="presentation" style="margin:4px 0 18px;border-collapse:collapse;">{rows}</table>' if rows else "")
    b_html = ""
    if button_label and button_url:
        b_html = (f'<p style="margin:22px 0 6px;"><a href="{escape(button_url, quote=True)}" '
                  f'style="display:inline-block;background:#1B2A6B;color:#FFFFFF;text-decoration:none;font-weight:600;'
                  f'font-size:15px;padding:12px 22px;border-radius:8px;">{escape(button_label)}</a></p>'
                  f'<p style="margin:10px 0 0;font-size:12px;color:#5A6385;word-break:break-all;">{escape(button_url)}</p>')
    html = (
        '<div style="background:#F4F6FB;padding:24px 12px;font-family:Segoe UI,Arial,sans-serif;">'
        '<div style="max-width:560px;margin:0 auto;background:#FFFFFF;border:1px solid #DDE2F0;border-radius:10px;overflow:hidden;">'
        '<div style="background:#1B2A6B;padding:14px 24px;color:#E2C46D;font-size:13px;letter-spacing:0.08em;font-weight:700;">'
        'BOTSWANA-UPENN PARTNERSHIP</div>'
        f'<div style="padding:24px;"><h1 style="margin:0 0 16px;font-family:Georgia,serif;font-size:21px;color:#1B2A6B;">{escape(heading)}</h1>'
        f'{p_html}{d_html}{b_html}</div>'
        '<div style="padding:14px 24px;border-top:1px solid #EEF0F8;font-size:12px;color:#5A6385;">'
        'This message was sent automatically by the BUP operations system. Please do not reply to it.</div>'
        '</div></div>'
    )
    lines = [heading, ""] + list(paragraphs)
    if details:
        lines += [""] + [f"{k}: {v}" for k, v in details]
    if button_label and button_url:
        lines += ["", f"{button_label}: {button_url}"]
    lines += ["", "This message was sent automatically by the BUP operations system. Please do not reply to it."]
    return html, "\n".join(lines)


def _explain_graph_error(response):
    try:
        error = json.loads(response.text).get("error", {})
        return f"HTTP {response.status_code} {error.get('code', 'Unknown')}: {error.get('message', response.text)}"
    except Exception:
        return f"HTTP {response.status_code}: {response.text[:300]}"


def send_email(to, subject, heading, paragraphs=(), details=(), button_label=None, button_url=None,
               attachments=(), event='', related_id=None):
    """
    Send one email through Microsoft Graph and record it in EmailLog.

    Never raises: an email problem must not undo or block a Study Bond step.
    Returns the EmailLog row (or None if there was nobody to send to).

    Safety rules, in order:
      - EMAIL_ENABLED off          -> nothing is sent, the log shows what WOULD have been sent.
      - DEBUG on, no redirect set  -> refused, so testing can never email real people.
      - EMAIL_REDIRECT_TO set      -> everything goes to that one address instead, subject marked [TEST].
    """
    try:
        from .models import EmailLog

        recipients = list(dict.fromkeys(a.strip() for a in to if a and a.strip()))
        if not recipients:
            logger.info("send_email(%s): no recipients, nothing to send", event)
            return None

        paragraphs = list(paragraphs)
        attachments = list(attachments)
        if sum(len(data) for _, data, _ in attachments) > MAX_ATTACHMENT_BYTES:
            attachments = []
            paragraphs.append("An attachment was too large to include in this email. "
                              "You can download it from the application page.")

        html_body, text_body = render_email(heading, paragraphs, details, button_label, button_url)

        redirect = getattr(settings, 'EMAIL_REDIRECT_TO', '') or ''
        actual, intended, final_subject = recipients, '', subject
        if redirect:
            intended = ', '.join(recipients)
            actual = [redirect]
            final_subject = f"[TEST for {intended}] {subject}"

        log = EmailLog.objects.create(
            event=event, to_addresses=', '.join(actual), intended_to=intended, subject=final_subject[:255],
            body_text=text_body, related_id=related_id, status=EmailLog.Status.SKIPPED,
        )

        if not getattr(settings, 'EMAIL_ENABLED', False):
            log.error = "Email is switched off (EMAIL_ENABLED is false), so nothing was sent."
            log.save(update_fields=['error'])
            return log
        if settings.DEBUG and not redirect:
            log.error = "Refused: DEBUG is on and EMAIL_REDIRECT_TO is not set, so real people would have been emailed."
            log.save(update_fields=['error'])
            return log

        sender = getattr(settings, 'GRAPH_SENDER_EMAIL', '')
        if not sender:
            log.status, log.error = EmailLog.Status.FAILED, "GRAPH_SENDER_EMAIL is not set."
            log.save(update_fields=['status', 'error'])
            return log

        message = {
            "subject": final_subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": a}} for a in actual],
        }
        if attachments:
            message["attachments"] = [
                {"@odata.type": "#microsoft.graph.fileAttachment", "name": name,
                 "contentType": content_type, "contentBytes": base64.b64encode(data).decode()}
                for name, data, content_type in attachments
            ]

        try:
            response = None
            for attempt in (1, 2):
                response = requests.post(
                    f"{GRAPH}/users/{sender}/sendMail",
                    headers={'Authorization': f"Bearer {_graph_token(force_new=(attempt == 2))}",
                             'Content-Type': 'application/json'},
                    json={"message": message, "saveToSentItems": False},
                    timeout=20,
                )
                if response.status_code != 401:
                    break
            if response.status_code == 202:
                log.status, log.sent_at = EmailLog.Status.SENT, timezone.now()
                log.save(update_fields=['status', 'sent_at'])
            else:
                log.status, log.error = EmailLog.Status.FAILED, _explain_graph_error(response)
                log.save(update_fields=['status', 'error'])
        except Exception as exc:
            log.status, log.error = EmailLog.Status.FAILED, f"{type(exc).__name__}: {exc}"
            log.save(update_fields=['status', 'error'])
        return log
    except Exception:
        logger.exception("send_email(%s) failed unexpectedly", event)
        return None
