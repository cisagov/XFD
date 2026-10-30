"""Django application configuration for tracker."""

# Third-Party Libraries
from django.apps import AppConfig


class TrackerConfig(AppConfig):
    """Configure the tracker Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tracker"
