"""Django application configuration for reports."""

# Third-Party Libraries
from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Configure the reports Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
