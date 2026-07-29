from django.shortcuts import redirect
from functools import wraps


def role_required(*roles):
    """
    Decorator that restricts a view to users with specific roles.
    Usage: @role_required('ADMIN', 'HR')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:access_denied')
            if request.user.role not in roles:
                return redirect('accounts:access_denied')
            if request.user.is_archived:
                return redirect('accounts:access_denied')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator