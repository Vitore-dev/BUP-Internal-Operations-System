from functools import wraps
from urllib.parse import urlencode
from django.shortcuts import redirect, get_object_or_404
from .models import StudyBondApplication


def _denied(reason):
    return redirect(f"/accounts/access-denied/?{urlencode({'reason': reason})}")


def owner_or_admin_hr_required(view_func):
    """
    Anyone with a legitimate stake in this specific application can view
    it: the employee who owns it, Admin/HR generally, or the specific
    person recorded as its approver/HR reviewer/finance processor —
    since they need to see the confirmation after acting on it.
    """
    @wraps(view_func)
    def wrapper(request, pk, *args, **kwargs):
        application = get_object_or_404(StudyBondApplication, pk=pk)
        is_stakeholder = request.user in (
            application.employee,
            application.approver,
            application.hr_reviewed_by,
            application.finance_processed_by,
        )
        if is_stakeholder or request.user.role in ('ADMIN', 'HR'):
            return view_func(request, pk, *args, **kwargs)
        return _denied("This application belongs to someone else, and you're not Admin/HR.")
    return wrapper


def hr_review_required(view_func):
    """
    HR/Admin only, AND the application must actually be waiting on HR.
    """
    @wraps(view_func)
    def wrapper(request, pk, *args, **kwargs):
        if request.user.role not in ('HR', 'ADMIN'):
            return _denied(f"HR review requires the HR or Admin role. Your role is {request.user.role or 'unassigned'}.")
        application = get_object_or_404(StudyBondApplication, pk=pk)
        if application.status != StudyBondApplication.Status.PENDING_HR_REVIEW:
            return redirect('employee_services:study_bond_detail', pk=pk)
        return view_func(request, pk, *args, **kwargs)
    return wrapper


def approver_required(view_func):
    """
    Only the specific person recorded as THIS application's approver can
    act on it — not "anyone with an elevated role", the actual individual.
    """
    @wraps(view_func)
    def wrapper(request, pk, *args, **kwargs):
        application = get_object_or_404(StudyBondApplication, pk=pk)
        if request.user != application.approver:
            approver_label = application.approver.username if application.approver else "no one"
            return _denied(
                f"Application #{pk}'s approver is {approver_label}. "
                f"You're logged in as {request.user.username}."
            )
        if application.status != StudyBondApplication.Status.PENDING_APPROVAL:
            return redirect('employee_services:study_bond_detail', pk=pk)
        return view_func(request, pk, *args, **kwargs)
    return wrapper


def finance_required(view_func):
    @wraps(view_func)
    def wrapper(request, pk, *args, **kwargs):
        if request.user.role not in ('FINANCE', 'ADMIN'):
            return _denied(f"Finance processing requires the Finance or Admin role. Your role is {request.user.role or 'unassigned'}.")
        application = get_object_or_404(StudyBondApplication, pk=pk)
        if application.status != StudyBondApplication.Status.PENDING_PAYMENT:
            return redirect('employee_services:study_bond_detail', pk=pk)
        return view_func(request, pk, *args, **kwargs)
    return wrapper