from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from .models import CustomUser, EmployeeProfile
from .forms import NameForm, SignatureForm
from .decorators import role_required


def access_denied(request):
    """
    Every access-control decorator in this project (role_required,
    approver_required, hr_review_required, finance_required) redirects
    here. Previously this always showed "no role assigned" regardless of
    the actual reason — which made object-level failures (e.g. "you're
    not this application's approver") look identical to a genuinely
    unassigned role. Callers now pass ?reason= so this shows the truth.
    """
    reason = request.GET.get('reason')
    if reason:
        message = f"Access Denied: {reason}"
    else:
        message = "Access Denied: Your account does not have a role assigned. Please contact IT Admin."
    # Plain text on purpose: the reason comes from the URL, so it must never be rendered as HTML.
    return HttpResponse(message, status=403, content_type='text/plain; charset=utf-8')


def _handle_profile_forms(request, user, redirect_name):
    profile, _ = EmployeeProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        name_form = NameForm(request.POST, instance=user)
        signature_form = SignatureForm(request.POST, request.FILES, instance=profile)
        if name_form.is_valid() and signature_form.is_valid():
            name_form.save()
            signature_form.save()

            from core.utils import log_action
            log_action(request, 'PROFILE_UPDATED', target_user=user,
                       description=f'Profile updated for {user}.')

            messages.success(request, 'Profile updated.')
            return redirect(redirect_name)
    else:
        name_form = NameForm(instance=user)
        signature_form = SignatureForm(instance=profile)

    return name_form, signature_form, profile


@login_required
def profile(request):
    """Self-service — employee edits their own name and signature."""
    result = _handle_profile_forms(request, request.user, 'accounts:profile')
    if isinstance(result, tuple):
        name_form, signature_form, profile_obj = result
        return render(request, 'accounts/profile.html', {
            'name_form': name_form,
            'signature_form': signature_form,
            'profile': profile_obj,
            'editing_self': True,
        })
    return result  # redirect


@login_required
@role_required('ADMIN', 'HR')
def admin_edit_profile(request, user_id):
    """Admin/HR editing another employee's profile from the directory."""
    target_user = get_object_or_404(CustomUser, id=user_id)
    result = _handle_profile_forms(request, target_user, 'hr:employee_directory')
    if isinstance(result, tuple):
        name_form, signature_form, profile_obj = result
        return render(request, 'accounts/profile.html', {
            'name_form': name_form,
            'signature_form': signature_form,
            'profile': profile_obj,
            'editing_self': False,
            'target_user': target_user,
        })
    return result  # redirect