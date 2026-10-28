"""URL configuration for the accounts application."""

# Third-Party Libraries
from django.urls.resolvers import URLPattern, URLResolver

app_name = "accounts"

urlpatterns: list[URLPattern | URLResolver] = []
