"""URL configuration for the operations application."""

# Third-Party Libraries
from django.urls.resolvers import URLPattern, URLResolver

app_name = "operations"

urlpatterns: list[URLPattern | URLResolver] = []
