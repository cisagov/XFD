"""Django application configuration for audit."""

# Third-Party Libraries
from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configure the audit Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
