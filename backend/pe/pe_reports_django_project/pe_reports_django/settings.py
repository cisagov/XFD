"""Django settings for the in-container PE worker API."""

# Standard Python Libraries
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_KEY", "pe-worker-local-dev-key")
DEBUG = os.environ.get("PE_API_DEBUG", "false").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "home.apps.HomeConfig",
    "dataAPI.apps.DataapiConfig",
]

MIDDLEWARE: list = []

ROOT_URLCONF = "pe_reports_django.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PE_DB_NAME", "pe"),
        "USER": os.environ.get("PE_DB_USERNAME", "pe"),
        "PASSWORD": os.environ.get("PE_DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", os.environ.get("PE_DB_HOST", "localhost")),
        "PORT": os.environ.get("PE_DB_PORT", "5432"),
    },
    # Crossfeed admin connection — used by pesyncdb to create the PE role/database.
    "admin": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": os.environ.get("DB_USERNAME", "crossfeed"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", os.environ.get("PE_DB_HOST", "localhost")),
        "PORT": os.environ.get("PE_DB_PORT", "5432"),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
PROJECT_NAME = "PE Worker API"
