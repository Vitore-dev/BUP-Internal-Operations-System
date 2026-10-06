from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import StudyBondApplication
from .routing import studies_for


@login_required
def staff_home(request):
    """
    The landing page for every employee, and the only home a research employee sees.
    Everything on it is read live and is about the signed-in person: their own
    applications, the studies they are on, and anything waiting for their decision.
    """
    user = request.user
    S = StudyBondApplication.Status

    mine = StudyBondApplication.objects.filter(employee=user).order_by('-submitted_at')
    returned = mine.filter(status=S.RETURNED)

    pending = StudyBondApplication.objects.filter(approver=user, status=S.PENDING_APPROVAL) \
        .select_related('employee').order_by('submitted_at')
    is_approver = pending.exists() or StudyBondApplication.objects.filter(approver=user).exists()

    my_studies = []
    for study in studies_for(user):
        if study.pi_id == user.id:
            role = 'PI'
        elif study.coordinator_id == user.id:
            role = 'Coordinator'
        else:
            role = 'Member'
        my_studies.append({'study': study, 'role': role})

    profile = getattr(user, 'employee_profile', None)

    return render(request, 'employee_services/staff_home.html', {
        'recent_applications': mine[:5],
        'returned_first': returned.first(),
        'returned_count': returned.count(),
        'pending_first': pending.first(),
        'pending_count': pending.count(),
        'is_approver': is_approver,
        'my_studies': my_studies,
        'profile_incomplete': not (profile and profile.profile_completed),
    })
