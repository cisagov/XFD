"""URL configuration for the tracker application."""

# Third-Party Libraries
from django.urls.resolvers import URLPattern, URLResolver

app_name = "tracker"

urlpatterns: list[URLPattern | URLResolver] = []
