from functools import wraps
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse


def _denied(reason):
    return redirect(f"{reverse('accounts:access_denied')}?{urlencode({'reason': reason})}")


def role_required(*roles):
    """
    Restricts a view to users with specific roles.
    Usage: @role_required('ADMIN', 'HR')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return _denied("Please sign in first.")
            if request.user.role not in roles:
                return _denied(f"This page is for {', '.join(roles)} only. Your role is {request.user.role or 'not assigned'}.")
            if request.user.is_archived:
                return _denied("This account has been archived.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
