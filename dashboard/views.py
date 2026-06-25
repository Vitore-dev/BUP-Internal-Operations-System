from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def admin_dashboard(request):
    return HttpResponse(f"✅ Admin Dashboard | User: {request.user.username} | Role: {request.user.role}")


@login_required
def hr_dashboard(request):
    return HttpResponse(f"✅ HR Dashboard | User: {request.user.username} | Role: {request.user.role}")


@login_required
def finance_dashboard(request):
    return HttpResponse(f"✅ Finance Dashboard | User: {request.user.username} | Role: {request.user.role}")


@login_required
def reception_dashboard(request):
    return HttpResponse(f"✅ Reception Dashboard | User: {request.user.username} | Role: {request.user.role}")


@login_required
def director_dashboard(request):
    return HttpResponse(f"✅ Director Dashboard | User: {request.user.username} | Role: {request.user.role}")


@login_required
def ops_dashboard(request):
    return HttpResponse(f"✅ Operations Manager Dashboard | User: {request.user.username} | Role: {request.user.role}")


@login_required
def pi_dashboard(request):
    return HttpResponse(f"✅ Project Coordinator Dashboard | User: {request.user.username} | Role: {request.user.role}")