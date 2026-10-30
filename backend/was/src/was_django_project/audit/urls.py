"""URL configuration for the audit application."""

# Third-Party Libraries
from django.urls.resolvers import URLPattern, URLResolver

app_name = "audit"

urlpatterns: list[URLPattern | URLResolver] = []
