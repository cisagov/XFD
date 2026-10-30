"""Django application configuration for stakeholders."""

# Third-Party Libraries
from django.apps import AppConfig


class StakeholdersConfig(AppConfig):
    """Configure the stakeholders Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "stakeholders"
