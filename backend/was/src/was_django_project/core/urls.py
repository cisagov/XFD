"""URL configuration for the core application."""

# Third-Party Libraries
from django.urls import path
from django.urls.resolvers import URLPattern, URLResolver

# Local Application
from . import views

app_name = "core"

urlpatterns: list[URLPattern | URLResolver] = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
]
