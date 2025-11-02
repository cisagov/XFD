"""App definition."""
# Third-Party Libraries
from django.apps import AppConfig


class XfdMiniDlConfig(AppConfig):
    """XFD datalake config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "xfd_mini_dl"
