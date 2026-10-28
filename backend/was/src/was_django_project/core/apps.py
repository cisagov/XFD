"""Django application configuration for core."""

# Third-Party Libraries
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configure the core Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
