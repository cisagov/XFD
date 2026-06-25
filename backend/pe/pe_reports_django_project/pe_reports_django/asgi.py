"""ASGI config for pe_reports_django project."""

# Standard Python Libraries
import os

# Third-Party Libraries
import django
from django.apps import apps
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.cors import CORSMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pe_reports_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Ensure apps are populated
apps.populate(settings.INSTALLED_APPS)


def get_application() -> FastAPI:
    """Get application."""
    # Import views after Django setup
    # Third-Party Libraries
    from dataAPI.views import api_router  # pylint: disable=C0415

    app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/apiv1")
    app.mount("/", WSGIMiddleware(get_wsgi_application()))
    return app


app = get_application()
