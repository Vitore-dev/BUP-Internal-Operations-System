import base64
import json
from datetime import datetime

import msal
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

GRAPH = "https://graph.microsoft.com/v1.0"


def token_roles(access_token):
    """
    The application permissions that are really active right now are listed in
    the token's 'roles' claim. Reading it separates "the permission isn't
    active yet" from "the permission is active but Exchange still refuses".
    """
    try:
        payload = access_token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get('roles', [])
    except Exception:
        return None


TOKEN_HINTS = (
    ("AADSTS7000215", "The client secret is wrong. Check AZURE_AD_CLIENT_SECRET in .env (use the secret VALUE, not its ID)."),
    ("AADSTS7000222", "The client secret has expired. Create a new secret in the Azure app registration and update .env."),
    ("AADSTS700016", "Azure can't find this app in the tenant. Check AZURE_AD_CLIENT_ID and AZURE_AD_TENANT_ID."),
    ("AADSTS90002", "The tenant id is wrong. Check AZURE_AD_TENANT_ID."),
)

SEND_HINTS = {
    "ErrorAccessDenied": (
        "Microsoft accepted the app's token but Exchange refused the send. Likely causes: "
        "(1) an Application Access Policy limits which mailboxes this app may use, and the sender is not "
        "one of them; (2) the permission was granted only minutes ago, so wait about 15 minutes and retry."
    ),
    "MailboxNotEnabledForRESTAPI": (
        "The sender mailbox is not an Exchange Online mailbox (it may be on-premises, unlicensed or "
        "inactive). Graph can only send from cloud mailboxes. Try another sender with --sender."
    ),
    "ErrorInvalidUser": "The sender address is not a valid mailbox in this tenant. Check GRAPH_SENDER_EMAIL.",
    "ResourceNotFound": "The sender address was not found in this tenant. Check GRAPH_SENDER_EMAIL.",
    "InvalidAuthenticationToken": "Graph did not accept the token. Re-run the command; if it repeats, the app registration needs checking.",
}


def explain_send_failure(status, body_text):
    """Turn Graph's error reply into the code, Microsoft's message, and a plain hint."""
    try:
        error = json.loads(body_text).get("error", {})
        code, message = error.get("code", "Unknown"), error.get("message", body_text)
    except Exception:
        code, message = "Unknown", body_text
    hint = SEND_HINTS.get(code, "No specific advice for this code. Send the full output above and we will work it out.")
    return code, message, hint


class Command(BaseCommand):
    help = "Send one test email through Microsoft Graph and say what the result means."

    def add_arguments(self, parser):
        parser.add_argument('recipient', help="Address to send the test message to")
        parser.add_argument('--sender', help="Send as this mailbox instead of GRAPH_SENDER_EMAIL")

    def handle(self, *args, **options):
        sender = options.get('sender') or settings.GRAPH_SENDER_EMAIL
        if not sender:
            raise CommandError("No sender. Set GRAPH_SENDER_EMAIL in .env or pass --sender.")

        cfg = settings.AZURE_AUTH
        self.stdout.write(f"Sender:    {sender}")
        self.stdout.write(f"Recipient: {options['recipient']}")

        app = msal.ConfidentialClientApplication(
            cfg['CLIENT_ID'], authority=cfg['AUTHORITY'], client_credential=cfg['CLIENT_SECRET'],
        )
        result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
        if 'access_token' not in result:
            description = result.get('error_description', '')
            hint = next((h for code, h in TOKEN_HINTS if code in description), "Check the three AZURE_AD_* values in .env.")
            raise CommandError(f"Step 1 failed: no token. {result.get('error')}\n{description}\nHint: {hint}")
        self.stdout.write(self.style.SUCCESS("Step 1 OK: got an access token."))

        roles = token_roles(result['access_token'])
        if roles is None:
            self.stdout.write("Step 2: could not read the token's permissions; trying the send anyway.")
        elif 'Mail.Send' in roles:
            self.stdout.write(self.style.SUCCESS("Step 2 OK: Mail.Send is active in the token."))
        else:
            self.stdout.write(self.style.WARNING(
                f"Step 2: Mail.Send is NOT in the token (it has: {', '.join(roles) or 'no application permissions'}). "
                "The permission may not be granted for this app, or was granted moments ago. Trying anyway."
            ))

        try:
            response = requests.post(
                f"{GRAPH}/users/{sender}/sendMail",
                headers={'Authorization': f"Bearer {result['access_token']}", 'Content-Type': 'application/json'},
                json={
                    "message": {
                        "subject": "bup_ops test email",
                        "body": {
                            "contentType": "Text",
                            "content": f"If you can read this, bup_ops can send email through Microsoft Graph.\nSent {datetime.now():%d %b %Y %H:%M}.",
                        },
                        "toRecipients": [{"emailAddress": {"address": options['recipient']}}],
                    },
                    "saveToSentItems": False,
                },
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            raise CommandError(f"Step 3 failed: could not reach Microsoft Graph ({exc}). Check this computer's internet or proxy.")

        if response.status_code == 202:
            self.stdout.write(self.style.SUCCESS(
                f"Step 3 OK: Microsoft accepted the message. Now check {options['recipient']}, including the spam folder."
            ))
            return

        code, message, hint = explain_send_failure(response.status_code, response.text)
        raise CommandError(f"Step 3 failed: HTTP {response.status_code}, {code}\nMicrosoft says: {message}\nWhat it usually means: {hint}")
