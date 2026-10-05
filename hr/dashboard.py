from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.decorators import role_required
from employee_services.models import StudyBondApplication
from .models import LetterRequest


@login_required
@role_required('HR', 'ADMIN')
def hr_home(request):
    """
    HR's landing page. Every number and row is read live from the Study Bond
    and letter-request tables; nothing here is stored.
    """
    S = StudyBondApplication.Status
    applications = StudyBondApplication.objects

    waiting = applications.filter(status=S.PENDING_HR_REVIEW) \
        .select_related('employee').order_by('submitted_at')
    waiting_count = waiting.count()

    stage_counts = {
        'hr_review': waiting_count,
        'approval': applications.filter(status=S.PENDING_APPROVAL).count(),
        'payment': applications.filter(status=S.PENDING_PAYMENT).count(),
        'completed': applications.filter(status=S.COMPLETED).count(),
    }

    recently_reviewed = applications.filter(hr_reviewed_by__isnull=False) \
        .select_related('employee').order_by('-hr_reviewed_at')[:5]

    pending_letters = LetterRequest.objects.filter(status='PENDING')
    letters_waiting = pending_letters.count()
    next_letter = pending_letters.select_related('requested_by').order_by('requested_at').first()

    profile = getattr(request.user, 'employee_profile', None)
    profile_incomplete = not (profile and profile.profile_completed)

    return render(request, 'hr/home.html', {
        'next_waiting': waiting.first(),
        'waiting_count': waiting_count,
        'stage_counts': stage_counts,
        'recently_reviewed': recently_reviewed,
        'letters_waiting': letters_waiting,
        'next_letter': next_letter,
        'profile_incomplete': profile_incomplete,
    })
