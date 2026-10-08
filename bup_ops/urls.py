"""
URL configuration for bup_ops project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('azure_auth.urls')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('hr/', include('hr.urls', namespace='hr')),
    path('', include('core.urls')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('director/', include('director.dashboard_urls', namespace='director')),
    path('employee-services/', include('employee_services.urls', namespace='employee_services')),
    path('onboarding/', include('onboarding.urls', namespace='onboarding')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)