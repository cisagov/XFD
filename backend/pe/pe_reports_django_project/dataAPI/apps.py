"""Django app configuration for PE FastAPI dataAPI routes."""

# Third-Party Libraries
from django.apps import AppConfig


class DataapiConfig(AppConfig):
    """Configure the dataAPI Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dataAPI"
