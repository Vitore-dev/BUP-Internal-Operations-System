def get_signature_image(user):
    """
    Signatures live on different models depending on the person's role —
    accounts.EmployeeProfile for baseline STAFF, director.DirectorProfile
    for the Director, and presumably hr.HRProfile follows the same
    pattern for HR staff. Rather than hardcode one of these (which is
    exactly the bug this function fixes), check each related profile a
    user might have and return whichever one actually carries a
    signature. Uses getattr defensively so an unexpected/renamed
    related_name never crashes PDF generation — it just falls through
    to the next candidate, or returns None if nobody has one on file.
    """
    for related_name in ('director_profile', 'hr_profile', 'finance_profile', 'employee_profile'):
        profile = getattr(user, related_name, None)
        signature = getattr(profile, 'signature_image', None) if profile else None
        if signature:
            return signature
    return None
