"""
URL configuration for was_django project.

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

# Third-Party Libraries
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("audit/", include("audit.urls")),
    path("operations/", include("operations.urls")),
    path("qualys_admin/", include("qualys_admin.urls")),
    path("reports/", include("reports.urls")),
    path("stakeholders/", include("stakeholders.urls")),
    path("tracker/", include("tracker.urls")),
]
