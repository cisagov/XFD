"""URL configuration for the core application."""

# Third-Party Libraries
from django.urls.resolvers import URLPattern, URLResolver

app_name = "core"

urlpatterns: list[URLPattern | URLResolver] = []
