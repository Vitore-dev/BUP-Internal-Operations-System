from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required


@login_required
def home_redirect(request):
    """
    Sends the logged-in user to their role-specific dashboard.
    """
    role = request.user.role

    role_url_map = {
        'ADMIN': '/dashboard/admin/',
        'HR': '/dashboard/hr/',
        'FINANCE': '/dashboard/finance/',
        #'RECEPTION': '/dashboard/reception/',
        'DIRECTOR': '/dashboard/director/',
        #'OPS_MANAGER': '/dashboard/ops/',
        'PI': '/dashboard/pi/',
    }


    url = role_url_map.get(role)

    if url:
        return redirect(url)
    else:
        return redirect('/accounts/access-denied/')
