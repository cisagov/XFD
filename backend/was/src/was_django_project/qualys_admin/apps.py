"""Django application configuration for Qualys administration."""

# Third-Party Libraries
from django.apps import AppConfig


class QualysAdminConfig(AppConfig):
    """Configure the Qualys administration Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "qualys_admin"
