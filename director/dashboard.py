from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.decorators import role_required
from employee_services.models import StudyBondApplication
from hr.models import ExtracurricularActivity


@login_required
@role_required('DIRECTOR', 'ADMIN')
def director_home(request):
    """
    The Director's landing page. Everything is read live:
    - Study Bond approvals are personal: only applications where THIS user
      is the recorded approver.
    - The pipeline counts are organisation-wide.
    - Extracurricular activities awaiting approval are shared: any submitted
      activity can be decided by the Director.
    """
    S = StudyBondApplication.Status
    applications = StudyBondApplication.objects

    my_waiting = applications.filter(approver=request.user, status=S.PENDING_APPROVAL) \
        .select_related('employee').order_by('submitted_at')
    waiting_count = my_waiting.count()

    stage_counts = {
        'hr_review': applications.filter(status=S.PENDING_HR_REVIEW).count(),
        'approval': applications.filter(status=S.PENDING_APPROVAL).count(),
        'payment': applications.filter(status=S.PENDING_PAYMENT).count(),
        'completed': applications.filter(status=S.COMPLETED).count(),
    }

    recent_decisions = applications.filter(approver=request.user, decision_date__isnull=False) \
        .select_related('employee').order_by('-decision_date')[:5]

    pending_activities = ExtracurricularActivity.objects.filter(status='SUBMITTED') \
        .select_related('submitted_by').order_by('proposed_date')
    activities_waiting = pending_activities.count()
    waiting_activities = list(pending_activities[:3])

    return render(request, 'director/home.html', {
        'next_waiting': my_waiting.first(),
        'waiting_count': waiting_count,
        'stage_counts': stage_counts,
        'recent_decisions': recent_decisions,
        'activities_waiting': activities_waiting,
        'waiting_activities': waiting_activities,
    })
