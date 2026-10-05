from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.conf import settings


@receiver(user_logged_in)
def populate_user_from_azure(sender, request, user, **kwargs):
    id_token_claims = request.session.get('id_token_claims', {})

    if not id_token_claims:
        return

    email = id_token_claims.get('preferred_username') or id_token_claims.get('upn')
    azure_oid = id_token_claims.get('oid')
    groups = id_token_claims.get('groups', [])

    role_priority = ['ADMIN', 'DIRECTOR', 'FINANCE', 'HR']

    group_role_map = {
        settings.AZURE_GROUPS.get('ADMIN'): 'ADMIN',
        settings.AZURE_GROUPS.get('HR'): 'HR',
        settings.AZURE_GROUPS.get('FINANCE'): 'FINANCE',
        #settings.AZURE_GROUPS.get('RECEPTION'): 'RECEPTION',
        settings.AZURE_GROUPS.get('DIRECTOR'): 'DIRECTOR',
        
    }

    matched_roles = [group_role_map[g] for g in groups if g in group_role_map]
    assigned_role = None
    for role in role_priority:
        if role in matched_roles:
            assigned_role = role
            break

    # No elevated Azure group matched. They're still a legitimate, authenticated
    # member of the org (Azure AD already confirmed that) — they just aren't in
    # one of the management/function groups. Fall back to the baseline role
    # instead of leaving them unassigned and locked out at home_redirect.
    #
    # This also self-heals a prior bug: if an elevated group is later *removed*
    # from someone's Azure account, this ensures their role correctly drops to
    # STAFF on next login instead of silently keeping stale elevated access.
    if not assigned_role:
        assigned_role = 'STAFF'

    updated = False

    if email and user.email != email:
        user.email = email
        updated = True

    if azure_oid and user.azure_id != azure_oid:
        user.azure_id = azure_oid
        updated = True

    if user.role != assigned_role:
        user.role = assigned_role
        updated = True

    if updated:
        user.save()

    # Write audit log entry for login
    from core.utils import log_action, get_client_ip
    from core.models import AuditLog
    AuditLog.objects.create(
        user=user,
        action='USER_LOGIN',
        description=f'{user.username} logged in via Azure AD',
        ip_address=get_client_ip(request),
    )


@receiver(user_logged_out)
def record_logout(sender, request, user, **kwargs):
    """Audit trail for sign-outs, the counterpart of the login entry written above."""
    if user is None:
        return
    from core.utils import get_client_ip
    from core.models import AuditLog
    AuditLog.objects.create(
        user=user,
        action='USER_LOGOUT',
        description=f'{user.username} signed out',
        ip_address=get_client_ip(request) if request else None,
    )
