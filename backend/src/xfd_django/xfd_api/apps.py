"""Django apps."""
# Third-Party Libraries
from django.apps import AppConfig


class XfdApiConfig(AppConfig):
    """Api config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "xfd_api"
