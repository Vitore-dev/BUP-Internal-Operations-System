from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings


@receiver(user_logged_in)
def populate_user_from_azure(sender, request, user, **kwargs):
    """
    After a successful Azure AD login, populate the CustomUser's
    email, role, and department based on the claims in their session.
    """
    id_token_claims = request.session.get('id_token_claims', {})

    if not id_token_claims:
        return

    email = id_token_claims.get('preferred_username') or id_token_claims.get('upn')
    azure_oid = id_token_claims.get('oid')
    groups = id_token_claims.get('groups', [])

    updated = False

    if email and user.email != email:
        user.email = email
        updated = True

    if azure_oid and user.azure_id != azure_oid:
        user.azure_id = azure_oid
        updated = True

    # Priority order matters if a user is in multiple groups during testing
    role_priority = ['ADMIN', 'DIRECTOR', 'FINANCE', 'HR', 'PI']

    group_role_map = {
        settings.AZURE_GROUPS.get('ADMIN'): 'ADMIN',
        settings.AZURE_GROUPS.get('HR'): 'HR',
        settings.AZURE_GROUPS.get('FINANCE'): 'FINANCE',
        #settings.AZURE_GROUPS.get('RECEPTION'): 'RECEPTION',
        settings.AZURE_GROUPS.get('DIRECTOR'): 'DIRECTOR',
        #settings.AZURE_GROUPS.get('OPS_MANAGER'): 'OPS_MANAGER',
        settings.AZURE_GROUPS.get('PI'): 'PI',
    }

    matched_roles = [group_role_map[g] for g in groups if g in group_role_map]
    assigned_role = None
    for role in role_priority:
        if role in matched_roles:
            assigned_role = role
            break

    if assigned_role and user.role != assigned_role:
        user.role = assigned_role
        updated = True

    if updated:
        user.save()