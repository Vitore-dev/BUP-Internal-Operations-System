from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse


def access_denied(request):
    return HttpResponse(
        "Access Denied: Your account does not have a role assigned. Please contact IT Admin.",
        status=403
    )
