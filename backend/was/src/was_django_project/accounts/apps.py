"""Django application configuration for accounts."""

# Third-Party Libraries
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configure the accounts Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
