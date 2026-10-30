"""URL configuration for the Qualys administration application."""

# Third-Party Libraries
from django.urls.resolvers import URLPattern, URLResolver

app_name = "qualys_admin"

urlpatterns: list[URLPattern | URLResolver] = []
