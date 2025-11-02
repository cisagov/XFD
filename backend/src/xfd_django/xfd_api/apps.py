"""
This module configures the Django application for the xfd_django project.

Classes:
    - XfdApiConfig: Configures the xfd_api application.
"""
# Third-Party Libraries
from django.apps import AppConfig


class XfdApiConfig(AppConfig):
    """
    Configure the xfd_api application.

    Attributes:
        default_auto_field (str): The default auto field type for models.
        name (str): The name of the application.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "xfd_api"
