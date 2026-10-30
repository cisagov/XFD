"""Django application configuration for operations."""

# Third-Party Libraries
from django.apps import AppConfig


class OperationsConfig(AppConfig):
    """Configure the operations Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "operations"
