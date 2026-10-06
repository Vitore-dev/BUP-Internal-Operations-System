from urllib.parse import urlencode

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

STAFF_HOME = '/employee-services/'


@login_required
def home_redirect(request):
    """
    Sends the logged-in user to their role-specific home page.

    Anyone whose role has no home of its own, whether the role is empty or
    one the system does not recognise, lands on the staff home. That page only
    ever shows the person's own applications, studies and services.
    """
    user = request.user

    # An archived account has left the organisation. Without this check, the staff-home
    # fallback below would let them in.
    if user.is_archived:
        reason = 'This account has been archived. Please contact IT Admin.'
        return redirect('/accounts/access-denied/?' + urlencode({'reason': reason}))

    role_url_map = {
        'ADMIN': '/dashboard/admin/',
        'HR': '/hr/',
        'FINANCE': '/finance/',
        #'RECEPTION': '/dashboard/reception/',
        'DIRECTOR': '/director/',
        #'OPS_MANAGER': '/dashboard/ops/',
        'STAFF': STAFF_HOME,
    }

    return redirect(role_url_map.get(user.role, STAFF_HOME))
