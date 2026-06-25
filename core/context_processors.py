def user_context(request):
    """
    Makes the logged-in user's role and department available
    in every template automatically.
    """
    if request.user.is_authenticated:
        return {
            'user_role': getattr(request.user, 'role', None),
            'user_department': getattr(request.user, 'department', None),
        }
    return {}








