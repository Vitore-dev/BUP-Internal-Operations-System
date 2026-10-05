from django.contrib.auth.decorators import login_required
from django.db.models import Max, Sum
from django.shortcuts import render

from accounts.decorators import role_required
from employee_services.models import StudyBondApplication
from .models import FinanceDocument


@login_required
@role_required('FINANCE', 'ADMIN')
def finance_home(request):
    """
    Finance's landing page. Everything on it is read live from the
    Study Bond and document-builder tables; nothing here is stored.
    """
    S = StudyBondApplication.Status
    applications = StudyBondApplication.objects

    awaiting = applications.filter(status=S.PENDING_PAYMENT).select_related('employee').order_by('decision_date')
    awaiting_count = awaiting.count()
    awaiting_total = awaiting.aggregate(total=Sum('amount_paid_by_bup'))['total']

    stage_counts = {
        'hr_review': applications.filter(status=S.PENDING_HR_REVIEW).count(),
        'approval': applications.filter(status=S.PENDING_APPROVAL).count(),
        'payment': awaiting_count,
        'completed': applications.filter(status=S.COMPLETED).count(),
    }

    recently_completed = applications.filter(finance_processed_by__isnull=False) \
        .select_related('employee').order_by('-finance_processed_at')[:5]

    recent_documents = FinanceDocument.objects.annotate(
        latest_version=Max('versions__version_number')
    ).order_by('-created_at')[:3]

    profile = getattr(request.user, 'employee_profile', None)
    profile_incomplete = not (profile and profile.profile_completed)

    return render(request, 'finance/home.html', {
        'next_payment': awaiting.first(),
        'awaiting_count': awaiting_count,
        'awaiting_total': awaiting_total,
        'stage_counts': stage_counts,
        'recently_completed': recently_completed,
        'recent_documents': recent_documents,
        'profile_incomplete': profile_incomplete,
    })
